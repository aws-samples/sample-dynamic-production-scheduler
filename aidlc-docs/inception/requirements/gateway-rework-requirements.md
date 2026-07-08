# AgentCore Gateway Rework — Requirements

## Intent Analysis
- **Request**: Migrate erp-data-mcp and audit-mcp from direct AgentCore Runtime deployment to AgentCore Gateway pattern
- **Request Type**: Architecture Migration
- **Scope**: Multiple components — 2 MCP servers, 4 agent configs, IAM roles, CDK infrastructure, gateway setup scripts
- **Complexity**: Moderate — well-defined target pattern (reference example), clear boundaries

## Functional Requirements

### FR-1: AgentCore Gateway
- Create a single AgentCore Gateway with MCP protocol type
- Gateway uses Cognito custom JWT authorizer
- Gateway has two targets: erp-data-mcp-target and audit-mcp-target
- Gateway endpoint format: `https://<gateway-id>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp`

### FR-2: Lambda Function Targets
- Repackage erp-data-mcp tool logic into a Lambda function handler
  - Lambda receives MCP tool calls via gateway, dispatches to existing tool functions
  - All 11 existing tools preserved: get_orders, get_order_by_id, update_order_priority, update_order_status, get_machine_capacity, get_manpower, get_materials, get_customers, get_running_tracker, update_running_tracker
- Repackage audit-mcp tool logic into a Lambda function handler
  - All 2 existing tools preserved: write_audit_entry, get_audit_trail
- Gateway targets define tool schemas (inlinePayload) matching existing tool signatures

### FR-3: Cognito OAuth Authentication
- CDK creates a Cognito User Pool for gateway authentication
- CDK creates an App Client with client_credentials grant type
- Two custom resource scopes:
  - `disruptionai-gateway/erp-data` — for ERP data MCP access
  - `disruptionai-gateway/audit` — for audit MCP access
- Gateway configured with custom JWT authorizer pointing to Cognito discovery URL

### FR-4: Agent Configuration Updates
- All 4 agents (orchestrator, impact-assessment, capacity-optimization, constraint-matching) updated:
  - Replace `mcp_gateway_url` (direct runtime URL) with gateway URL
  - Replace `audit_mcp_url` (orchestrator only) with gateway URL
  - Replace `mcp-proxy-for-aws` SigV4 auth with Cognito OAuth2 credential provider
- Agents authenticate via OAuth2 tokens obtained from Cognito credential provider registered in AgentCore Identity

### FR-5: Gateway Setup Scripts
- Python scripts in `infrastructure/scripts/`:
  - `create_gateway.py` — creates the AgentCore Gateway with Cognito JWT auth
  - `create_erp_data_target.py` — creates erp-data-mcp Lambda target with tool schemas
  - `create_audit_target.py` — creates audit-mcp Lambda target with tool schemas
  - `gateway_observability.py` — enables CloudWatch logging for gateway
  - `cognito_oauth_setup.py` — creates OAuth authorizer via GatewayClient (or manual Cognito config)
  - `cognito_credentials_provider.py` — manages OAuth2 credential providers for agents

### FR-6: IAM Permission Rework
- New dedicated gateway IAM role (CDK-managed):
  - `bedrock-agentcore:CreateGateway`, `GetGateway`, `DeleteGateway`
  - `bedrock-agentcore:CreateGatewayTarget`, `GetGatewayTarget`, `DeleteGatewayTarget`
  - `lambda:InvokeFunction` on both MCP Lambda functions
- Lambda execution roles for each MCP Lambda:
  - erp-data-mcp Lambda: DynamoDB read/write (same as current runtime role)
  - audit-mcp Lambda: DynamoDB audit table read/write (same as current runtime role)
- Agent execution roles updated:
  - Remove `bedrock-agentcore:InvokeAgentRuntime` for MCP runtimes
  - Add gateway invocation permissions
- Cognito permissions for gateway role

### FR-7: Remove Direct Runtime Deployments
- Remove erp_data_mcp and audit_mcp entries from `.bedrock_agentcore.yaml`
- Remove `apply-dynamodb-permissions.sh` (replaced by CDK-managed Lambda roles)
- Update `apply-cross-agent-permissions.sh` to exclude MCP runtime roles

## Non-Functional Requirements

### NFR-1: Security (SECURITY extension enabled)
- SECURITY-01: Lambda functions use encrypted environment variables, DynamoDB encryption at rest
- SECURITY-03: Lambda functions include structured logging to CloudWatch
- SECURITY-05: Tool input validation preserved (existing Pydantic schemas)
- SECURITY-06: Least-privilege IAM — Lambda roles scoped to specific DynamoDB tables, gateway role scoped to specific resources
- SECURITY-08: Gateway enforces Cognito JWT authentication on all requests
- SECURITY-12: No hardcoded credentials — Cognito secrets managed via CDK/Secrets Manager

### NFR-2: Observability
- Gateway CloudWatch logging enabled
- Lambda function CloudWatch log groups with 90-day retention
- Gateway access logs for audit trail

### NFR-3: Backward Compatibility
- All existing MCP tool signatures preserved exactly
- Agent behavior unchanged — only transport layer changes
- No changes to business logic in tool implementations

## Architecture Summary

```
Current:
  Agent --> SigV4 --> AgentCore Runtime (MCP Server)

Target:
  Agent --> OAuth2 Token --> AgentCore Gateway --> Lambda Function --> DynamoDB
```

## Affected Components
| Component | Change Type |
|-----------|------------|
| erp-data-mcp | Major — repackage as Lambda |
| audit-mcp | Major — repackage as Lambda |
| orchestrator-agent/config.py | Minor — URL + auth change |
| impact-assessment-agent/config.py | Minor — URL + auth change |
| capacity-optimization-agent/config.py | Minor — URL + auth change |
| constraint-matching-agent/config.py | Minor — URL + auth change |
| All agent agent.py files | Minor — MCP client factory change |
| infrastructure/lib/iam-stack.ts | Major — new roles + policies |
| infrastructure/lib/ (new stacks) | New — Cognito, Lambda, Gateway role |
| infrastructure/scripts/ | New — gateway setup scripts |
| .bedrock_agentcore.yaml | Minor — remove MCP entries |
