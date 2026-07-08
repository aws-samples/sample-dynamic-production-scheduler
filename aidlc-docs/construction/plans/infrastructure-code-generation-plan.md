# Code Generation Plan — Unit 9: Infrastructure (CDK)

## Unit Context

Unit 9 provisions all AWS infrastructure for DisruptionAI using TypeScript AWS CDK. Infrastructure requirements are aggregated from Units 1-8 infrastructure design artifacts.

**Project Structure**: `infrastructure/` at workspace root
**Language**: TypeScript
**Framework**: AWS CDK v2
**Deployment**: `cdk deploy`

## Resource Inventory (from Units 1-8)

### DynamoDB Tables (Unit 1 + Unit 3)
- disruptionai-orders (PK: order_id, GSI: plant-status-index)
- disruptionai-capacity (PK: machine_type, SK: plant)
- disruptionai-manpower (PK: plant)
- disruptionai-materials (PK: material_type, SK: plant)
- disruptionai-customers (PK: customer_id)
- disruptionai-tracker (PK: session_id)
- disruptionai-audit (PK: session_id, SK: entry_id, GSI: session-agent-index, PITR enabled)

### Frontend Hosting (Unit 8)
- S3 bucket (private, OAI, versioning, SSE-S3, public access blocked)
- CloudFront distribution (HTTPS, security headers, SPA routing, OAI)
- CloudFront response headers policy (CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy)

### Monitoring (All Units)
- CloudWatch log groups (90-day retention): /disruptionai/erp-data-mcp, /disruptionai/audit-mcp, /disruptionai/impact-assessment-agent, /disruptionai/capacity-optimization-agent, /disruptionai/constraint-matching-agent, /disruptionai/orchestrator-agent, /disruptionai/websocket-api

### WebSocket API (Unit 7 + Unit 8)
- API Gateway WebSocket API ($connect, $disconnect, sendMessage routes)
- Lambda integration for WebSocket handler
- Stage: prod

### IAM (All Units)
- ECS task role (DynamoDB + CloudWatch for MCP servers)
- Agent roles (Bedrock invoke + AgentCore + CloudWatch per agent)
- WebSocket Lambda role
- CDK deployment role

## Code Generation Steps

### Step 1: Project Setup
- [x] Initialize CDK TypeScript project in `infrastructure/`
- [x] Create package.json, tsconfig.json, cdk.json
- [x] Define CDK app entry point (bin/app.ts)

### Step 2: Database Stack
- [x] Create `lib/database-stack.ts`
- [x] 7 DynamoDB tables with On-Demand billing, AWS-managed encryption
- [x] GSI on orders table (plant-status-index)
- [x] GSI on audit table (session-agent-index)
- [x] PITR enabled on audit table
- [x] Export table name outputs

### Step 3: Monitoring Stack
- [x] Create `lib/monitoring-stack.ts`
- [x] 7 CloudWatch log groups with 90-day retention
- [x] CloudWatch dashboard with key metrics
- [x] CloudWatch alarms (DynamoDB throttle, Lambda errors, 5xx on API GW)

### Step 4: Frontend Hosting Stack
- [x] Create `lib/frontend-stack.ts`
- [x] S3 bucket (private, versioning, SSE-S3, block public access)
- [x] CloudFront OAI
- [x] CloudFront distribution (HTTPS redirect, SPA error responses)
- [x] Response headers policy (SECURITY-04 headers)
- [x] S3 bucket policy for OAI access
- [x] CloudFront access logging to separate log bucket

### Step 5: WebSocket API Stack
- [x] Create `lib/websocket-stack.ts`
- [x] API Gateway WebSocket API
- [x] $connect, $disconnect, sendMessage routes
- [x] Lambda handler placeholder (integration point for orchestrator)
- [x] Stage deployment (prod)
- [x] IAM role for Lambda with CloudWatch + invoke permissions

### Step 6: IAM Stack
- [x] Create `lib/iam-stack.ts`
- [x] ECS task execution role
- [x] ECS task role with DynamoDB + CloudWatch permissions (least-privilege per table)
- [x] WebSocket Lambda execution role
- [x] Export role ARN outputs

### Step 7: CDK App Entry Point
- [x] Create `bin/app.ts` wiring all stacks with dependencies
- [x] Stack dependency ordering (Database -> Monitoring -> IAM -> WebSocket -> Frontend)
- [x] Environment configuration (account, region)

### Step 8: Unit Tests
- [x] Create `test/database-stack.test.ts` — snapshot + assertion tests
- [x] Create `test/monitoring-stack.test.ts` — log group retention assertions
- [x] Create `test/frontend-stack.test.ts` — S3 + CloudFront assertions
- [x] Create `test/websocket-stack.test.ts` — API GW + Lambda assertions
- [x] Create `test/iam-stack.test.ts` — least-privilege policy assertions

### Step 9: Documentation and Summary
- [x] Create `infrastructure/README.md`
- [x] Create `aidlc-docs/construction/infrastructure/code/code-generation-summary.md`
- [x] Update aidlc-state.md — Unit 9 Code Generation = COMPLETE

## Security Compliance Notes

All stacks must enforce:
- SECURITY-01: Encryption at rest (DynamoDB default, S3 SSE-S3) + TLS in transit
- SECURITY-02: CloudFront access logging, API GW execution logging
- SECURITY-04: Response headers on CloudFront
- SECURITY-06: Least-privilege IAM (specific actions, specific resource ARNs)
- SECURITY-07: No 0.0.0.0/0 inbound except CloudFront
- SECURITY-09: S3 public access blocked, no default credentials
- SECURITY-10: Pinned CDK construct versions in package.json
- SECURITY-14: 90-day log retention, app roles cannot delete own logs

## Story Traceability

Unit 9 supports ALL stories (US-01 through US-10) as infrastructure foundation.
