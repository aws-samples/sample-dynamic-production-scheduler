# AgentCore Gateway Rework — Clarifying Questions

Please answer the following questions to help clarify the rework requirements.

## Question 1
How should the two MCP servers be organized behind the gateway?

A) Single gateway with two targets — one target for erp-data-mcp (Lambda or Runtime), one target for audit-mcp (Lambda or Runtime)
B) Single gateway with a single combined target — merge both MCP servers into one Lambda function
C) Two separate gateways — one gateway per MCP server
D) Other (please describe after [Answer]: tag below)

[Answer]: A, lambda targets for both

## Question 2
What authentication mechanism should the gateway use?

A) Amazon Cognito OAuth (custom JWT authorizer) — matching the device-management-agent reference example exactly
B) IAM-based authentication only (no Cognito) — agents authenticate via SigV4 to the gateway
C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
Should the MCP servers remain deployed as AgentCore Runtime instances (current state), or should they be migrated to Lambda functions behind the gateway (like the device-management-agent reference)?

A) Keep as AgentCore Runtime — gateway targets point to the existing runtime endpoints
B) Migrate to Lambda functions — repackage MCP tool logic into Lambda handlers, gateway targets point to Lambda ARNs
C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 4
For the gateway setup scripts, what format do you prefer?

A) Python scripts (matching the reference example pattern — create_gateway.py, create_target.py, cognito_setup.py, observability.py)
B) Shell scripts (bash, using AWS CLI directly)
C) CDK infrastructure-as-code (add gateway resources to the existing CDK stacks)
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
Should the gateway setup scripts and credential provider scripts live in a new top-level `gateway/` directory (like the reference example), or somewhere else?

A) New top-level `gateway/` directory (matching reference example structure)
B) Inside `infrastructure/scripts/` alongside existing deployment scripts
C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6
For the agent-side changes (orchestrator, impact-assessment, capacity-optimization, constraint-matching), how should they authenticate to the gateway?

A) Cognito OAuth2 credential provider — agents obtain OAuth tokens via a credential provider registered in AgentCore Identity (matching reference example)
B) Keep current SigV4 auth via mcp-proxy-for-aws — just change the endpoint URL to the gateway URL
C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
Should the existing direct-runtime MCP deployment (.bedrock_agentcore.yaml entries for erp_data_mcp and audit_mcp) be removed/replaced, or kept alongside the gateway as a fallback?

A) Replace — remove the direct runtime deployments, gateway becomes the only access path
B) Keep both — maintain direct runtime as fallback, add gateway as primary path
C) Other (please describe after [Answer]: tag below)

[Answer]: Replace

## Question 8
What scope of IAM permission changes do you expect?

A) Full rework — create a dedicated gateway IAM role, update agent execution roles to invoke gateway instead of direct runtime, add Cognito permissions
B) Minimal — only add gateway-specific permissions to existing roles
C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9
Should the rework include updating the existing CDK infrastructure stacks (e.g., adding a Cognito User Pool, gateway IAM role), or should these be managed outside CDK via scripts?

A) Add to CDK — create new stacks or extend existing ones for Cognito, gateway role, etc.
B) Scripts only — manage gateway infrastructure via Python/bash scripts (like the reference example)
C) Hybrid — Cognito and IAM roles in CDK, gateway creation via scripts
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10
Security extension is enabled. For the gateway's Cognito OAuth setup, what scope configuration do you want?

A) Single custom scope (e.g., `disruptionai-gateway/invoke`) — all agents share the same scope
B) Per-MCP-server scopes (e.g., `disruptionai-gateway/erp-data`, `disruptionai-gateway/audit`) — fine-grained access control
C) Other (please describe after [Answer]: tag below)

[Answer]: B
