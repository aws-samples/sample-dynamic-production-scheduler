# Gateway Rework — Code Generation Plan

## Overview
Migrate erp-data-mcp and audit-mcp from direct AgentCore Runtime to AgentCore Gateway with Lambda targets and Cognito OAuth. 4 parallel work streams.

## Stream 1: Lambda Function Handlers
- [x] Step 1.1: Create `erp-data-mcp/src/erp_data_mcp/lambda_handler.py` — Lambda handler dispatching to existing tool functions (10 tools)
- [x] Step 1.2: Create `audit-mcp/src/audit_mcp/lambda_handler.py` — Lambda handler dispatching to existing tool functions (2 tools)

## Stream 2: CDK Infrastructure
- [x] Step 2.1: Create `infrastructure/lib/cognito-stack.ts` — Cognito User Pool, App Client, Resource Server with custom scopes
- [x] Step 2.2: Create `infrastructure/lib/mcp-lambda-stack.ts` — Lambda functions for both MCPs with DynamoDB permissions
- [x] Step 2.3: Create `infrastructure/lib/gateway-iam-stack.ts` — Gateway IAM role, agent gateway invoke permissions
- [x] Step 2.4: Update `infrastructure/bin/app.ts` — Wire new stacks into CDK app
- [x] Step 2.5: Update `infrastructure/lib/iam-stack.ts` — Add gateway invoke permissions to ECS task role (agents use this)

## Stream 3: Gateway Setup Scripts
- [x] Step 3.1: Create `infrastructure/scripts/create_gateway.py` — Create AgentCore Gateway with Cognito JWT authorizer
- [x] Step 3.2: Create `infrastructure/scripts/create_erp_data_target.py` — Create erp-data-mcp Lambda target with tool schemas
- [x] Step 3.3: Create `infrastructure/scripts/create_audit_target.py` — Create audit-mcp Lambda target with tool schemas
- [x] Step 3.4: Create `infrastructure/scripts/gateway_observability.py` — Enable CloudWatch logging for gateway
- [x] Step 3.5: Create `infrastructure/scripts/cognito_credentials_provider.py` — Register OAuth2 credential providers for agents

## Stream 4: Agent Config Updates
- [x] Step 4.1: Update `orchestrator-agent/src/orchestrator_agent/config.py` — Replace runtime URLs with gateway URL + Cognito config
- [x] Step 4.2: Update `orchestrator-agent/src/orchestrator_agent/agent.py` — Replace SigV4 MCP client with Cognito OAuth MCP client (both ERP + Audit)
- [x] Step 4.3: Update `impact-assessment-agent/src/impact_assessment_agent/config.py` — Gateway URL + Cognito config
- [x] Step 4.4: Update `impact-assessment-agent/src/impact_assessment_agent/agent.py` — Cognito OAuth MCP client
- [x] Step 4.5: Update `capacity-optimization-agent/src/capacity_optimization_agent/config.py` — Gateway URL + Cognito config
- [x] Step 4.6: Update `capacity-optimization-agent/src/capacity_optimization_agent/agent.py` — Cognito OAuth MCP client
- [x] Step 4.7: Update `constraint-matching-agent/src/constraint_matching_agent/config.py` — Gateway URL + Cognito config
- [x] Step 4.8: Update `constraint-matching-agent/src/constraint_matching_agent/agent.py` — Cognito OAuth MCP client
- [x] Step 4.9: Update `.bedrock_agentcore.yaml` — Cleared to default_agent: null / agents: {}
- [x] Step 4.10: Update `infrastructure/scripts/apply-cross-agent-permissions.sh` — Add gateway invoke statement
- [x] Step 4.11: Delete `infrastructure/scripts/apply-dynamodb-permissions.sh` — Replaced by CDK-managed Lambda roles

## Security Compliance (SECURITY extension enabled)
- SECURITY-01: DynamoDB encryption at rest (existing), Lambda env vars encrypted by default
- SECURITY-03: Structured logging in Lambda handlers to CloudWatch
- SECURITY-05: Input validation via existing Pydantic schemas in tool functions
- SECURITY-06: Least-privilege IAM — Lambda roles scoped to specific tables, gateway role scoped
- SECURITY-08: Gateway enforces Cognito JWT auth on all requests
- SECURITY-09: No default credentials, generic error responses in Lambda
- SECURITY-10: Lock files committed, pinned dependencies
- SECURITY-12: No hardcoded credentials — Cognito secrets via CDK, env vars for config
- SECURITY-14: CloudWatch log retention 90 days, gateway access logging
- SECURITY-15: Fail-closed error handling in Lambda handlers
