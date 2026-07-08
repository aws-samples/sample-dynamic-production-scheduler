# Gateway Rework — Execution Plan

## Scope
Migrate erp-data-mcp and audit-mcp from direct AgentCore Runtime to AgentCore Gateway with Lambda targets and Cognito OAuth.

## Phases to Execute

### INCEPTION PHASE (Rework Cycle 2)
- [x] Workspace Detection — COMPLETE
- [x] Requirements Analysis — COMPLETE
- [x] Workflow Planning — IN PROGRESS
- [ ] User Stories — SKIP (pure infrastructure migration, no user-facing changes)
- [ ] Application Design — SKIP (existing component boundaries unchanged)
- [ ] Units Generation — SKIP (reusing existing unit structure)

### CONSTRUCTION PHASE
- [ ] Functional Design — SKIP (business logic unchanged, only transport layer)
- [ ] NFR Requirements — SKIP (existing NFRs still apply)
- [ ] NFR Design — SKIP (patterns unchanged)
- [ ] Infrastructure Design — EXECUTE (new gateway + Lambda + Cognito architecture)
- [ ] Code Generation — EXECUTE (4 parallel work streams)
- [ ] Build and Test — EXECUTE

## Code Generation Work Streams (Parallelizable)

### Stream 1: Lambda Functions (erp-data-mcp + audit-mcp)
- Create Lambda handler for erp-data-mcp (dispatches to existing tool functions)
- Create Lambda handler for audit-mcp (dispatches to existing tool functions)
- Lambda packaging config (requirements, deployment)

### Stream 2: CDK Infrastructure
- New cognito-stack.ts (User Pool, App Client, Resource Server, custom scopes)
- New gateway-stack.ts (Gateway IAM role, Lambda execution roles)
- New lambda-stack.ts (Lambda functions for both MCPs)
- Update iam-stack.ts (remove old runtime permissions)

### Stream 3: Gateway Setup Scripts
- create_gateway.py
- create_erp_data_target.py
- create_audit_target.py
- gateway_observability.py
- cognito_credentials_provider.py

### Stream 4: Agent Config Updates
- Update all 4 agent config.py files (gateway URL, remove direct runtime URL)
- Update all agent agent.py files (MCP client factory — Cognito OAuth instead of SigV4)
- Update .bedrock_agentcore.yaml (remove MCP entries)
- Update cross-agent permissions script

## Risk Assessment
- **Risk Level**: Medium
- **Rollback**: Can revert to direct runtime by restoring .bedrock_agentcore.yaml and agent configs
- **Testing**: Gateway connectivity test, Lambda invocation test, end-to-end agent test
