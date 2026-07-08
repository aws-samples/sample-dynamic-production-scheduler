# Application Design — DisruptionAI (Consolidated)

## Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent tool granularity | Coarse-grained | Fewer tools, simpler agent prompts, each tool does one complete operation |
| Shared agent context | AgentCore Memory | Managed service, replaces manual DynamoDB session management |
| Mock ERP data storage | DynamoDB | Persistent mock data, AgentCore Memory only for inter-agent context |
| Agent communication | MCP for data access, Strands SDK tool calls for agent-to-agent | MCP wraps external data; Orchestrator invokes agents as tools |
| Running capacity tracker | DynamoDB (via MCP) | Shared between frontend and backend, persists across reconnects |
| What-if recalculation | Incremental | Only re-run affected agents, not full restart |
| Frontend-backend boundary | Split | Frontend manages UI state, backend manages business logic and persistence |
| Orchestration pattern | Mixed tool call | Parallel tool calls for Round 1, sequential tool calls for Round 2 (Capacity & Optimization for delays, then Constraint Matching for funnel) |

---

## Architecture Overview

DisruptionAI is a 4-layer system:

1. **Frontend Layer** — React SPA with Chat Interface and Side Panel
2. **Backend Services Layer** — WebSocket Handler and Session Manager on ECS/Fargate
3. **Agent Layer** — 4 Strands SDK agents (Orchestrator, Impact Assessment, Capacity & Optimization, Constraint Matching)
4. **Data Access Layer** — 3 MCP servers (ERP Data, Weather, Audit) wrapping DynamoDB and mock APIs

### Key Architectural Patterns

- **Orchestrator as coordinator**: Orchestrator Agent manages the entire workflow, invoking sub-agents as Strands SDK tools
- **MCP for data access**: All external data (DynamoDB, weather API) accessed through MCP servers, decoupling agents from storage
- **AgentCore Memory for shared context**: Managed service for inter-agent state (prioritized orders, capacity snapshot)
- **WebSocket for streaming**: Bidirectional streaming via API Gateway WebSocket API
- **Incremental what-if**: Only affected agents re-execute on what-if questions
- **Delay optimization in Capacity & Optimization Agent**: Delay candidate identification, freed capacity calculation, and delay approval handling are co-located with capacity analysis for tight feedback loops
- **Constraint Matching Agent focused**: 4-layer funnel operates on post-delay capacity, cleanly separated from delay logic

---

## Component Summary

### Agent Layer (4 agents)

| Agent | Role | Orchestration Pattern | Data Access |
|-------|------|----------------------|-------------|
| Orchestrator | Workflow coordinator, conversation manager | Entry point (invoked by WebSocket Handler) | Weather MCP, Audit MCP, AgentCore Memory |
| Impact Assessment | Florida order prioritization (P1/P2/P3) | Tool call (parallel, Round 1) | ERP Data MCP, AgentCore Memory (write) |
| Capacity & Optimization | Ohio capacity analysis + delay optimization | Tool call (parallel Round 1, sequential Round 2) | ERP Data MCP, AgentCore Memory (write) |
| Constraint Matching | 4-layer constraint funnel, order-by-order scheduling | Tool call (sequential, Round 2) | ERP Data MCP, AgentCore Memory (read) |

### MCP Servers (3 servers)

| Server | Purpose | Tools | Storage |
|--------|---------|-------|---------|
| ERP Data | Mock ERP data access | get_orders, get_machine_capacity, get_manpower, get_materials, get_customers, update_order_priority, update_order_status, get/update_running_tracker | DynamoDB |
| Weather | Mock disruption events | get_active_events, get_plant_impact | In-memory |
| Audit | Decision audit trail | write_audit_entry, get_audit_trail | DynamoDB |

### Backend Services (2 services)

| Service | Purpose | Dependencies |
|---------|---------|-------------|
| WebSocket Handler | Connection management, message routing, streaming relay | Orchestrator Agent, Session Manager |
| Session Manager | Session lifecycle, AgentCore Memory interface | AgentCore Memory |

### Frontend Components (2 components)

| Component | Purpose | Key Features |
|-----------|---------|-------------|
| Chat Interface | Conversational UI | Streaming tokens, agent badges, inline tables, expandable reasoning |
| Side Panel | Structured approval and monitoring | Approve/Reject/Skip buttons, capacity tracker, audit trail, phase progress |

---

## Execution Flow Summary

### Phase 0: Disruption Alert
```
Weather MCP --> Orchestrator --> "Tornado approaching Florida, 20 orders at risk"
Planner confirms --> Orchestrator starts workflow
```

### Phase 1 + 2: Round 1 (Parallel)
```
Orchestrator fires in parallel:
  Impact Assessment Agent   --> ERP Data MCP --> classify orders --> AgentCore Memory
  Capacity & Optimization   --> ERP Data MCP --> analyze capacity --> AgentCore Memory
```

### Phase 3: Round 2 (Sequential Interactive)
```
Orchestrator invokes Capacity & Optimization Agent:
  Step 1: Identify delay candidates --> Planner approves/rejects each
          Recalculate capacity post-delays --> AgentCore Memory

Orchestrator invokes Constraint Matching Agent:
  Step 2: 4-layer constraint funnel per Florida order (P1 first)
          --> Present recommendation --> Planner approves/skips/rejects
          --> Update running tracker --> Next order
```

### What-If Flow
```
Planner asks what-if --> Orchestrator identifies affected agent(s)
  --> Re-invoke affected agent with modified params (incremental)
  --> Update shared context --> Re-evaluate current order
```

---

## Security Considerations (SECURITY Extension)

| Rule | Applicability | Design Impact |
|------|--------------|---------------|
| SECURITY-01 | DynamoDB encryption | Enable encryption at rest, enforce TLS |
| SECURITY-02 | API Gateway logging | Enable access logging on WebSocket API |
| SECURITY-03 | Application logging | Structured logging with correlation IDs in all agents and services |
| SECURITY-04 | N/A for MVP | No HTML-serving endpoints (SPA served from S3/CloudFront) |
| SECURITY-05 | WebSocket messages | Validate all incoming WebSocket message payloads |
| SECURITY-06 | IAM policies | Least-privilege for ECS task role, DynamoDB access, Bedrock access |
| SECURITY-07 | VPC/Security groups | Restrict inbound to API Gateway only, agents in private subnet |
| SECURITY-08 | N/A for MVP | No authentication (deferred), but design for future Cognito integration |
| SECURITY-09 | Error handling | Generic error messages to frontend, no stack traces |
| SECURITY-10 | Dependencies | Lock files, vulnerability scanning in build |
| SECURITY-11 | Rate limiting | Rate limit WebSocket messages, security modules isolated |
| SECURITY-12 | N/A for MVP | No authentication (deferred) |
| SECURITY-13 | SRI, pipeline | SRI for CDN resources, pipeline access control |
| SECURITY-14 | Alerting | CloudWatch alarms for error rates, log retention 90+ days |
| SECURITY-15 | Error handling | Global error handler, fail-closed, resource cleanup |

---

## Cross-References

- **Detailed component definitions**: `components.md`
- **Method signatures**: `component-methods.md`
- **Service orchestration patterns**: `services.md`
- **Dependency relationships**: `component-dependency.md`
- **Requirements**: `aidlc-docs/inception/requirements/requirements.md`
- **User stories**: `aidlc-docs/inception/user-stories/stories.md`
