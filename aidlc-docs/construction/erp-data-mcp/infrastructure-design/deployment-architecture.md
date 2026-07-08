# Deployment Architecture — Unit 1: ERP Data MCP Server

## Deployment Model

The ERP Data MCP Server is NOT an independently deployed service. It runs as a Python subprocess within the ECS container that hosts the agent layer.

```
+-------------------------------------------------------+
|  ECS Fargate Task                                     |
|                                                       |
|  +------------------+     +------------------------+  |
|  | Agent Process    |     | ERP Data MCP Server    |  |
|  | (Python)         | --> | (Python subprocess)    |  |
|  |                  |     |                        |  |
|  | - Orchestrator   |     | - 10 MCP tools         |  |
|  | - Prod Order Agt |     | - Pydantic validation  |  |
|  | - Capacity Agt   |     | - boto3 DynamoDB       |  |
|  | - Scheduler Agt  |     | - JSON logging         |  |
|  +------------------+     +------------------------+  |
|         |                          |                  |
|         | stdio                    | HTTPS             |
|         v                          v                  |
|  +------------------+     +------------------------+  |
|  | Strands SDK      |     | DynamoDB (6 tables)    |  |
|  | MCP Client       |     |                        |  |
|  +------------------+     +------------------------+  |
+-------------------------------------------------------+
```

## Communication

- **Agent to MCP Server**: stdio transport (stdin/stdout pipes)
- **MCP Server to DynamoDB**: HTTPS via boto3 SDK (TLS 1.2+)
- **No network ports exposed**: MCP server has no HTTP listener

## Process Lifecycle

1. ECS task starts the agent process (main entry point)
2. Agent process spawns ERP Data MCP Server as subprocess
3. Strands SDK MCP client connects via stdio pipes
4. Agent invokes MCP tools through Strands SDK tool interface
5. MCP server queries/updates DynamoDB and returns results
6. On task shutdown, subprocess terminates with parent

## Environment Variables

Injected by ECS task definition (values from CDK stack outputs):

| Variable | Source |
|----------|--------|
| AWS_REGION | CDK stack region |
| DYNAMODB_TABLE_ORDERS | CDK output |
| DYNAMODB_TABLE_CAPACITY | CDK output |
| DYNAMODB_TABLE_MANPOWER | CDK output |
| DYNAMODB_TABLE_MATERIALS | CDK output |
| DYNAMODB_TABLE_CUSTOMERS | CDK output |
| DYNAMODB_TABLE_TRACKER | CDK output |
| LOG_LEVEL | Task definition (INFO) |

## IAM

- MCP server inherits the ECS task role
- Task role includes DynamoDB and CloudWatch permissions defined in infrastructure-design.md
- No separate IAM role for the MCP server subprocess

## Packaging

- MCP server packaged as a Python package within the ECS container image
- Installed via `pip install -e ./erp-data-mcp` in Dockerfile
- Entry point: `python -m erp_data_mcp.server`
