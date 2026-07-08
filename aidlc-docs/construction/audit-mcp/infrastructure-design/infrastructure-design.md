# Infrastructure Design — Unit 3: Audit MCP Server

## Infrastructure Mapping

| Logical Component | AWS Service | Configuration |
|-------------------|-------------|---------------|
| Audit Data Store | DynamoDB | Table: disruptionai-audit, PAY_PER_REQUEST |
| MCP Server Runtime | ECS/Fargate (subprocess) | Runs alongside agent container |
| Logging | CloudWatch Logs | Via stdout from container |

## DynamoDB Table: disruptionai-audit

- **Partition Key**: `session_id` (S)
- **Sort Key**: `entry_id` (S)
- **GSI**: `session-agent-index` (PK: session_id, SK: agent, Projection: ALL)
- **Billing**: PAY_PER_REQUEST (on-demand)
- **Encryption**: AWS managed keys (default)
- **Point-in-time Recovery**: Enabled
- **TTL**: Not enabled (audit data retained indefinitely for MVP)

## Network
- No direct network access — runs as subprocess via stdio
- DynamoDB access via AWS SDK (boto3) through container IAM role
