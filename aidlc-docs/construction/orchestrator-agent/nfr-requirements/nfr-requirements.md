# NFR Requirements — Unit 7: Orchestrator Agent

## Performance Requirements

### PERF-OA-01: Round 1 End-to-End Time
- Full Round 1 (Impact Assessment + Capacity Analysis) must complete within 90 seconds
- Includes: two sub-agent invocations via AgentCore API, shared context writes, LLM summary generation
- Sub-agents run sequentially (LLM-driven tool calls), each budgeted at ~30s

### PERF-OA-02: Sub-Agent Invocation Latency
- Individual sub-agent invocation via AgentCore managed runtime API must return within 45 seconds
- Includes: AgentCore API call overhead (~200ms), sub-agent LLM reasoning, MCP tool calls
- Timeout at 45s — triggers retry per BR-OA-08

### PERF-OA-03: What-If Recalculation Time
- Single what-if recalculation must complete within 30 seconds
- Involves re-invoking one or two sub-agents with modified parameters
- LLM routing decision (which agents to call) should take < 2 seconds

### PERF-OA-04: Streaming Token Latency
- Time-to-first-token for Orchestrator's own responses: < 1 second
- Sub-agent token relay latency: < 500ms additional overhead vs direct sub-agent streaming
- Structured data payloads (tables, tracker) delivered as complete JSON within 2 seconds of generation

### PERF-OA-05: Session State Operations
- AgentCore Memory read/write: < 500ms per operation
- WorkflowSession state update: < 100ms (in-process dataclass mutation)

---

## Reliability Requirements

### REL-OA-01: Sub-Agent Failure Recovery
- Retry once on sub-agent failure (BR-OA-08)
- Continue with partial results if retry fails (Round 1: present available agent's results)
- Critical failure (both Round 1 agents fail): halt workflow, explain to Planner
- All failures logged as AgentError entities and audit entries

### REL-OA-02: Session Persistence
- WorkflowSession written to AgentCore Memory after every phase transition
- On reconnection, session can be restored from AgentCore Memory
- If AgentCore Memory read fails on reconnection, start fresh session

### REL-OA-03: LLM Retry Strategy
- Bedrock ThrottlingException: retry with exponential backoff (1s, 2s, 4s — 3 attempts max)
- Bedrock ModelErrorException: fail immediately, report to Planner
- Bedrock timeout: fail after 30 seconds, report to Planner
- Strands SDK handles retry internally via agent config

### REL-OA-04: Idempotency
- Orchestrator workflow is NOT idempotent (stateful conversation)
- However, individual sub-agent invocations are idempotent (same input = same output)
- Re-invoking a sub-agent after failure produces consistent results

### REL-OA-05: Graceful Degradation
- If Audit MCP is unavailable: log warning, continue workflow without audit writes
- If AgentCore Memory is unavailable: fall back to in-process session state (no recovery on disconnect)
- If one sub-agent is permanently unavailable: skip that agent's contribution, inform Planner

---

## Observability Requirements

### OBS-OA-01: Structured Logging
- Python `logging` module with JSON formatter (consistent with Units 1-6)
- Log every sub-agent invocation: agent_id, input summary, duration, success/failure
- Log every phase transition: old_phase, new_phase, timestamp
- Log every Planner decision: order_id, decision_type, round
- Log every what-if request: question summary, agents re-invoked

### OBS-OA-02: Log Fields
Every log entry includes:
- `timestamp` (ISO 8601)
- `level` (ERROR, WARNING, INFO)
- `agent_name` ("orchestrator_agent")
- `session_id` (workflow session correlation)
- `phase` (current WorkflowPhase)
- `duration_ms` (for timed operations)
- `message` (human-readable)

### OBS-OA-03: Log Destination
- stdout (captured by AgentCore runtime logging)
- CloudWatch Log Group: `/disruptionai/orchestrator-agent`
- Log retention: 90 days minimum (SECURITY-14 compliance)

### OBS-OA-04: Audit Trail Integration
- All workflow-level events written to Audit MCP (per BR-OA-10)
- 9 action types defined in domain-entities.md
- Audit entries are the primary decision record; agent logs are supplementary

---

## Security Requirements (SECURITY Extension)

### SEC-OA-01: Input Validation (SECURITY-05)
- All Planner messages validated: max 4000 chars, sanitized for injection (BR-OA-15)
- Sub-agent responses validated before processing
- WebSocket message payloads validated against expected schema

### SEC-OA-02: No Hardcoded Credentials (SECURITY-12)
- Bedrock credentials via IAM role (AgentCore managed runtime)
- Sub-agent IDs and MCP Gateway URLs configurable via environment variables
- No API keys or secrets in source code

### SEC-OA-03: Least Privilege (SECURITY-06)
- Agent IAM role scoped to:
  - `bedrock:InvokeModel` on Claude 4.5 Haiku model ARN only
  - `bedrock-agentcore:InvokeAgent` on sub-agent ARNs only
  - MCP tool access controlled by AgentCore Gateway authorization
- No direct DynamoDB access

### SEC-OA-04: Error Sanitization (SECURITY-09)
- Error messages to Planner are generic — no stack traces or internal details
- Full error context logged server-side only
- Sub-agent error details not exposed to Planner (only summary messages)

### SEC-OA-05: Fail Closed (SECURITY-15)
- On unhandled exception: return error to Planner, do not proceed
- Global exception handler wraps agent entry point
- Sub-agent failures handled per BR-OA-08 (retry + partial results)

### SEC-OA-06: Session Security
- Session IDs are UUIDs — not guessable
- Session state in AgentCore Memory scoped by session_id
- No cross-session data leakage

---

## Scalability Requirements

### SCALE-OA-01: Concurrent Sessions
- MVP: single concurrent session (one Planner at a time)
- Architecture supports multiple sessions via session_id scoping
- No shared mutable state between sessions

### SCALE-OA-02: AgentCore Hosting
- Agent registered in Bedrock AgentCore managed runtime
- AgentCore handles scaling, health checks, and lifecycle
- Single-user MVP — no horizontal scaling needed
