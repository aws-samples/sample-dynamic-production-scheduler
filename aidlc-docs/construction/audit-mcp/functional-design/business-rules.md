# Business Rules — Unit 3: Audit MCP Server

## BR-01: Entry ID Generation
- Every audit entry MUST receive a server-generated UUID v4 as `entry_id`
- Clients MUST NOT provide `entry_id`

## BR-02: Timestamp Validation
- `timestamp` MUST be a valid ISO 8601 string
- `timestamp` MUST NOT be in the future (tolerance: 60 seconds)

## BR-03: Agent Validation
- `agent` MUST be one of: `orchestrator`, `production_order_agent`, `capacity_agent`, `scheduler_agent`, `planner`
- Invalid agent values MUST be rejected with INVALID_INPUT error

## BR-04: Session ID Required
- `session_id` is required for both write and read operations
- Empty or missing `session_id` MUST be rejected with INVALID_INPUT error

## BR-05: Audit Trail Query Filtering
- `get_audit_trail` MUST support filtering by `session_id` (required)
- Optional filter by `agent` — returns only entries from that agent
- Optional filter by `start_time` — returns entries with `timestamp >= start_time`
- Results MUST be sorted by `timestamp` ascending (oldest first)

## BR-06: Immutability
- Audit entries MUST NOT be updated or deleted after creation
- The MCP server MUST NOT expose update or delete tools for audit entries
