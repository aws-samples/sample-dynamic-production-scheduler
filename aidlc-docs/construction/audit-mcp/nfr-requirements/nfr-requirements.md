# NFR Requirements — Unit 3: Audit MCP Server

## Performance
- Write latency: < 200ms p99 for single audit entry writes
- Read latency: < 500ms p99 for session audit trail queries (up to 500 entries)
- Throughput: Support 10 concurrent write operations per session

## Availability
- Runs as subprocess alongside agents — availability tied to agent container
- DynamoDB on-demand capacity — no provisioning needed for MVP

## Security
- No PII in audit entries (agent names, order IDs, actions only)
- Structured logging to stdout — no secrets in logs
- Input validation on all parameters (Pydantic)
- DynamoDB encryption at rest (AWS managed keys)

## Reliability
- Fail-closed error handling — DynamoDB errors return INTERNAL_ERROR, never partial data
- Idempotent writes via unique entry_id (UUID v4)

## Maintainability
- Same project structure as ERP Data MCP (consistent patterns)
- Pydantic schemas for all inputs
- Structured JSON logging
