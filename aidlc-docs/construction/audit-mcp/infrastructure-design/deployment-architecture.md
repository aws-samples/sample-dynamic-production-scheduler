# Deployment Architecture — Unit 3: Audit MCP Server

## Deployment Model
- Same as Unit 1: Python subprocess using stdio transport
- Packaged as pip-installable Python package
- Runs inside ECS/Fargate container alongside Orchestrator Agent
- Entry point: `audit-mcp-server` CLI command

## Container Integration
- Installed in same Docker image as agent layer
- Orchestrator Agent spawns as subprocess via Strands SDK MCP integration
- Communicates via stdin/stdout (MCP stdio transport)

## IAM Permissions Required
- `dynamodb:PutItem` on `disruptionai-audit` table
- `dynamodb:Query` on `disruptionai-audit` table and `session-agent-index` GSI
- No delete or update permissions (immutable audit trail)
