# Code Generation Summary — Gateway Rework (Rework Cycle 2)

## Overview
Migrated erp-data-mcp and audit-mcp from direct AgentCore Runtime invocation to AgentCore Gateway with Lambda targets and Cognito OAuth authentication. All 4 agents updated to use Cognito OAuth MCP clients.

## Files Created (12)

| File | Purpose |
|------|---------|
| `erp-data-mcp/src/erp_data_mcp/lambda_handler.py` | Lambda handler dispatching 10 ERP tools with Pydantic validation |
| `audit-mcp/src/audit_mcp/lambda_handler.py` | Lambda handler dispatching 2 audit tools |
| `infrastructure/lib/cognito-stack.ts` | Cognito User Pool, Resource Server (per-MCP scopes), App Client |
| `infrastructure/lib/mcp-lambda-stack.ts` | Two Lambda functions with least-privilege DynamoDB IAM |
| `infrastructure/lib/gateway-iam-stack.ts` | Gateway management role for script-based setup |
| `infrastructure/scripts/create_gateway.py` | Creates AgentCore Gateway with Cognito JWT authorizer |
| `infrastructure/scripts/create_erp_data_target.py` | Registers erp-data-mcp Lambda target (10 tool schemas) |
| `infrastructure/scripts/create_audit_target.py` | Registers audit-mcp Lambda target (2 tool schemas) |
| `infrastructure/scripts/gateway_observability.py` | Enables CloudWatch logging on gateway |
| `infrastructure/scripts/cognito_credentials_provider.py` | Registers OAuth2 credential providers for agents |

## Files Modified (10)

| File | Changes |
|------|---------|
| `infrastructure/bin/app.ts` | Added CognitoStack, McpLambdaStack, GatewayIamStack |
| `infrastructure/lib/iam-stack.ts` | Added AgentCoreGatewayInvoke policy to ECS task role |
| `orchestrator-agent/src/orchestrator_agent/config.py` | Replaced runtime URLs with gateway_url + cognito fields |
| `orchestrator-agent/src/orchestrator_agent/agent.py` | Cognito OAuth MCP client (ERP + Audit) |
| `impact-assessment-agent/src/impact_assessment_agent/config.py` | Gateway URL + cognito fields |
| `impact-assessment-agent/src/impact_assessment_agent/agent.py` | Cognito OAuth MCP client |
| `capacity-optimization-agent/src/capacity_optimization_agent/config.py` | Gateway URL + cognito fields |
| `capacity-optimization-agent/src/capacity_optimization_agent/agent.py` | Cognito OAuth MCP client |
| `constraint-matching-agent/src/constraint_matching_agent/config.py` | Gateway URL + cognito fields |
| `constraint-matching-agent/src/constraint_matching_agent/agent.py` | Cognito OAuth MCP client |

## Files Cleared (1)

| File | Changes |
|------|---------|
| `.bedrock_agentcore.yaml` | Cleared to `default_agent: null` / `agents: {}` (MCPs no longer deployed as Runtime) |

## Files Updated (1)

| File | Changes |
|------|---------|
| `infrastructure/scripts/apply-cross-agent-permissions.sh` | Added gateway invoke permission statement |

## Files Deleted (1)

| File | Reason |
|------|--------|
| `infrastructure/scripts/apply-dynamodb-permissions.sh` | Replaced by CDK-managed Lambda IAM roles |

## Security Compliance Summary

| Rule | Status | Notes |
|------|--------|-------|
| SECURITY-01 | Compliant | DynamoDB encryption at rest (existing), Lambda env vars encrypted by default |
| SECURITY-02 | N/A | Gateway access logging handled by gateway_observability.py script |
| SECURITY-03 | Compliant | Structured logging in Lambda handlers to CloudWatch |
| SECURITY-04 | N/A | No HTML-serving endpoints in this rework |
| SECURITY-05 | Compliant | Input validation via existing Pydantic schemas in tool functions |
| SECURITY-06 | Compliant | Least-privilege IAM — Lambda roles scoped to specific DynamoDB tables |
| SECURITY-07 | N/A | No network configuration changes in this rework |
| SECURITY-08 | Compliant | Gateway enforces Cognito JWT auth on all MCP requests |
| SECURITY-09 | Compliant | No default credentials, generic error responses in Lambda handlers |
| SECURITY-10 | Compliant | Lock files committed, pinned dependencies |
| SECURITY-11 | Compliant | Security logic isolated (auth in gateway, validation in handlers) |
| SECURITY-12 | Compliant | No hardcoded credentials — Cognito secrets via CDK, env vars for config |
| SECURITY-13 | N/A | No deserialization of untrusted data, no CDN resources |
| SECURITY-14 | Compliant | CloudWatch log retention 90 days, gateway access logging via script |
| SECURITY-15 | Compliant | Fail-closed error handling in Lambda handlers, global try/catch |
