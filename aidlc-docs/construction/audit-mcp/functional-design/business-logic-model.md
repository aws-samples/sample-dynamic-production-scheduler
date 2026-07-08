# Business Logic Model — Unit 3: Audit MCP Server

## Tool 1: write_audit_entry

### Input
| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `session_id` | String | Yes | Non-empty, max 128 chars |
| `agent` | String | Yes | Must be valid agent enum value |
| `action` | String | Yes | Non-empty, max 256 chars |
| `details` | Dict | Yes | Non-empty dict |
| `timestamp` | String | Yes | Valid ISO 8601, not future |

### Logic
1. Validate all input fields via Pydantic schema
2. Generate UUID v4 for `entry_id`
3. Generate server-side `created_at` timestamp
4. Write item to DynamoDB audit table
5. Return `{ "entry_id": "<uuid>", "status": "created" }`

### Error Responses
- INVALID_INPUT: Validation failure (bad agent, future timestamp, missing fields)
- INTERNAL_ERROR: DynamoDB write failure

## Tool 2: get_audit_trail

### Input
| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `session_id` | String | Yes | Non-empty, max 128 chars |
| `agent` | String | No | Must be valid agent enum if provided |
| `start_time` | String | No | Valid ISO 8601 if provided |

### Logic
1. Validate input via Pydantic schema
2. If `agent` filter provided: Query GSI `session-agent-index`
3. Else: Query table by `session_id` partition key
4. If `start_time` provided: Apply filter expression `timestamp >= start_time`
5. Sort results by `timestamp` ascending
6. Return `{ "entries": [...], "count": <n> }`

### Error Responses
- INVALID_INPUT: Validation failure
- INTERNAL_ERROR: DynamoDB query failure
