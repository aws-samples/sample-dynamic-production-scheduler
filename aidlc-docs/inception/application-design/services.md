# Services — DisruptionAI

## Service Layer Overview

The service layer orchestrates the interaction between the frontend, agents, data access, and shared memory. The Orchestrator Agent acts as the primary service coordinator.

---

## Orchestration Patterns

### Pattern Selection by Agent Type

| Agent | Pattern | Rationale |
|-------|---------|-----------|
| Orchestrator | Entry point (WebSocket handler invokes) | Top-level coordinator, manages conversation |
| Impact Assessment Agent | Tool call (parallel) | Orchestrator fires as tool in Round 1, runs concurrently with Capacity & Optimization Agent |
| Capacity & Optimization Agent | Tool call (parallel + sequential) | Orchestrator fires as tool in Round 1 (capacity analysis), then again in Round 2 (delay optimization) |
| Constraint Matching Agent | Tool call (sequential, interactive) | Orchestrator invokes for Round 2 constraint funnel after delays are resolved |

### Round 1: Parallel Intelligence Gathering

```
Orchestrator
    |
    +---> [parallel] Impact Assessment Agent (tool call)
    |         |
    |         +--> MCP: get_orders(plant="Florida")
    |         +--> Apply priority algorithm
    |         +--> AgentCore Memory: write prioritized orders
    |
    +---> [parallel] Capacity & Optimization Agent (tool call)
              |
              +--> MCP: get_machine_capacity, get_manpower, get_materials
              +--> Calculate surplus, identify bottleneck
              +--> AgentCore Memory: write capacity snapshot
```

### Round 2: Sequential Interactive Scheduling

```
Orchestrator
    |
    +--> Step 1: Capacity & Optimization Agent (tool call)
    |    |
    |    +--> AgentCore Memory: read existing Ohio orders
    |    +--> Identify delay candidates (P3, deadline > 6 weeks)
    |    +--> Present each candidate to Planner (via Orchestrator relay)
    |    +--> Planner approves/rejects each delay
    |    +--> Recalculate capacity post-delays
    |    +--> AgentCore Memory: write updated capacity snapshot
    |    +--> MCP: update_running_tracker
    |
    +--> Step 2: Constraint Matching Agent (tool call)
         |
         +--> AgentCore Memory: read prioritized orders + updated capacity
         +--> 4-layer constraint funnel
              +--> For each Florida order (P1 first):
                   +--> Run 4 layers
                   +--> Present recommendation to Planner
                   +--> Planner approves/skips/rejects
                   +--> MCP: update_running_tracker
```

### What-If Recalculation (Incremental)

```
Planner: "What if I add weekend shifts?"
    |
    v
Orchestrator
    |
    +--> Determine affected agent(s): Capacity & Optimization Agent
    +--> Re-invoke Capacity & Optimization Agent with modified parameters
    +--> Capacity & Optimization Agent recalculates with weekend shifts enabled
    +--> AgentCore Memory: update capacity snapshot
    +--> Constraint Matching Agent: re-evaluate current order with new capacity
    +--> Stream updated recommendation to Planner
```

---

## Data Flow Services

### MCP Data Access Service

All agents access external data through MCP servers. This provides a standardized interface and decouples agents from storage implementation.

```
Agent --> MCP Client --> MCP Server --> DynamoDB / Mock API
```

- Agents use Strands SDK MCP integration to call MCP tools
- Each MCP server is a separate Python process (stdio transport for local, SSE for remote)
- MCP servers handle DynamoDB queries, data transformation, and error handling

### AgentCore Memory Service

Shared agent context flows through AgentCore Memory:

```
Impact Assessment Agent    --> AgentCore Memory: write("prioritized_orders", [...])
Capacity & Optimization    --> AgentCore Memory: write("capacity_snapshot", {...})
Constraint Matching Agent  --> AgentCore Memory: read("prioritized_orders")
Constraint Matching Agent  --> AgentCore Memory: read("capacity_snapshot")
```

- Session-scoped: context tied to a workflow session
- Managed service: no manual DynamoDB table management for agent state
- Agents read/write using session ID as the key scope

### Running Capacity Tracker Service

The running tracker lives in DynamoDB (via MCP ERP Data Server) and is updated after each order decision:

```
Constraint Matching Agent decides order
    |
    +--> MCP: update_running_tracker(session_id, updated_tracker)
    +--> WebSocket: stream updated tracker to frontend
    +--> Frontend Side Panel: re-render tracker display
```

---

## Streaming Service

### Token Streaming Pipeline

```
Agent generates token
    |
    v
Strands SDK callback
    |
    v
WebSocket Handler: stream_response(connection_id, token)
    |
    v
API Gateway WebSocket: relay to client
    |
    v
React Chat Interface: handleStreamToken(token)
```

- Strands SDK provides streaming callbacks during agent execution
- WebSocket Handler relays tokens to the connected frontend
- Frontend appends tokens to the current message bubble
- Structured data (tables) is sent as a complete JSON payload after streaming text

### Message Types (WebSocket Protocol)

| Type | Direction | Payload |
|------|-----------|---------|
| `user_message` | Frontend -> Backend | `{ text, session_id }` |
| `stream_token` | Backend -> Frontend | `{ token, agent_name }` |
| `stream_end` | Backend -> Frontend | `{ agent_name }` |
| `structured_data` | Backend -> Frontend | `{ type: "table"/"tracker", data }` |
| `approval_request` | Backend -> Frontend | `{ order_id, recommendation, funnel_results }` |
| `approval_response` | Frontend -> Backend | `{ order_id, decision: "approve"/"reject"/"skip" }` |
| `phase_update` | Backend -> Frontend | `{ phase, status }` |
| `error` | Backend -> Frontend | `{ message, code }` |

---

## Error Handling Service

### Agent Error Recovery

- If an agent tool call fails, Orchestrator retries once
- If retry fails, Orchestrator informs Planner with error context
- Partial results are preserved (e.g., if Capacity & Optimization Agent fails but Impact Assessment Agent succeeded, Round 1 partial results are available)

### WebSocket Reconnection

- Frontend implements exponential backoff reconnection
- On reconnect, Session Manager restores last known state from AgentCore Memory
- Running capacity tracker restored from DynamoDB

---

## Security Service Integration

Per SECURITY extension rules:
- All WebSocket connections over WSS (TLS 1.2+)
- Input validation on all WebSocket messages (SECURITY-05)
- Rate limiting on WebSocket message frequency (SECURITY-11)
- Structured logging with correlation IDs (SECURITY-03)
- No secrets in logs (SECURITY-03)
- Global error handler returns generic messages (SECURITY-15)
