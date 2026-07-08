# Domain Entities — Unit 3: Audit MCP Server

## AuditEntry

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entry_id` | String (UUID) | Auto-generated | Unique identifier for the audit entry |
| `session_id` | String | Yes | Workflow session identifier |
| `agent` | String (enum) | Yes | Agent that performed the action |
| `action` | String | Yes | Action performed (e.g., "prioritize_order", "approve_reroute") |
| `details` | Map/Dict | Yes | Structured details of the action |
| `timestamp` | String (ISO 8601) | Yes | When the action occurred |
| `created_at` | String (ISO 8601) | Auto-generated | Server-side creation timestamp |

### Agent Enum Values
- `orchestrator`
- `production_order_agent`
- `capacity_agent`
- `scheduler_agent`
- `planner` (for human decisions)

### DynamoDB Table Schema

- **Table Name**: `disruptionai-audit`
- **Partition Key**: `session_id` (String)
- **Sort Key**: `entry_id` (String)
- **GSI**: `session-agent-index`
  - Partition Key: `session_id`
  - Sort Key: `agent`
  - Projection: ALL
