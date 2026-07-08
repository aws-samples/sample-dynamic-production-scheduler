# Deployment Plan — DisruptionAI

## Overview

DisruptionAI is a multi-component system deployed to AWS. This plan covers the end-to-end deployment sequence from AWS account prerequisites through production readiness verification.

## Target Architecture

```
Internet
    |
    v
+-----------------------------------------------+
| CloudFront (CDN)                              |
| - React SPA (S3 origin)                      |
| - Security headers (CSP, HSTS, etc.)         |
+-----------------------------------------------+
    |
    v
+-----------------------------------------------+
| API Gateway WebSocket API (wss://)            |
| - $connect / $disconnect / sendMessage        |
| - Lambda handler (routing + connection mgmt)  |
+-----------------------------------------------+
    |
    v
+-----------------------------------------------+
| Bedrock AgentCore Managed Runtime             |
|                                               |
| +-------------------------------------------+ |
| | Orchestrator Agent                        | |
| | - Invokes sub-agents via AgentCore API    | |
| +-------------------------------------------+ |
|       |           |           |               |
|       v           v           v               |
| +-----------+ +---------+ +-----------+       |
| | Impact    | | Cap &   | | Constraint|       |
| | Assess.   | | Optim.  | | Matching  |       |
| +-----------+ +---------+ +-----------+       |
|                                               |
| +-------------------------------------------+ |
| | AgentCore Runtime                       | |
| | - ERP Data MCP (HTTP/SSE)                 | |
| | - Audit MCP (HTTP/SSE)                    | |
| +-------------------------------------------+ |
+-----------------------------------------------+
    |
    v
+-----------------------------------------------+
| DynamoDB (7 tables, On-Demand)                |
| - orders, capacity, manpower, materials       |
| - customers, tracker, audit                   |
+-----------------------------------------------+
    |
    v
+-----------------------------------------------+
| CloudWatch                                    |
| - 7 log groups (90-day retention)             |
| - Dashboard, alarms, metric filters          |
+-----------------------------------------------+
```

---

## Prerequisites

### AWS Account Setup

| Requirement | Details |
|-------------|---------|
| AWS Account | Active account with billing enabled |
| Region | us-east-1 (default, configurable) |
| AWS CLI | v2 installed and configured |
| CDK CLI | v2.178.0+ (`npm install -g aws-cdk`) |
| CDK Bootstrap | `cdk bootstrap aws://ACCOUNT/us-east-1` |
| Bedrock Access | Claude 4.5 Haiku model enabled in Bedrock console |
| AgentCore Access | Bedrock AgentCore service enabled |

### Local Build Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | MCP servers and agents |
| Node.js | 18+ | Frontend build and CDK |
| npm | 9+ | Package management |
| pip | Latest | Python package management |
| Docker | Latest | (Optional) Local testing |

### Bedrock Model Access

Before deployment, enable the following in the AWS Bedrock console:
1. Navigate to Bedrock > Model access
2. Request access to Claude 4.5 Haiku (Anthropic)
3. Wait for access to be granted (usually immediate)

---

## Deployment Sequence

Deployment follows a strict dependency order. Each phase must complete before the next begins.

### Phase 1: Infrastructure Foundation (CDK Deploy)

Deploy all 5 CDK stacks in dependency order:

```bash
cd infrastructure
npx cdk deploy --all --require-approval broadening
```

This deploys stacks in the correct order (CDK resolves dependencies):

1. **DisruptionAI-Database** — 7 DynamoDB tables + GSIs
2. **DisruptionAI-Monitoring** — 7 CloudWatch log groups, dashboard, alarms
3. **DisruptionAI-IAM** — ECS task role + execution role (depends on Database + Monitoring)
4. **DisruptionAI-WebSocket** — API Gateway WebSocket API + Lambda handler (depends on Monitoring)
5. **DisruptionAI-Frontend** — S3 bucket + CloudFront distribution (depends on WebSocket)

**Verification**:
```bash
# Confirm all stacks deployed
npx cdk list
aws cloudformation describe-stacks --query "Stacks[?starts_with(StackName,'DisruptionAI')].{Name:StackName,Status:StackStatus}" --output table
```

**Expected outputs** (captured as CloudFormation exports):
- `disruptionai-table-orders`, `disruptionai-table-capacity`, etc. (7 table names)
- `disruptionai-ecs-task-role-arn`, `disruptionai-ecs-execution-role-arn`
- `disruptionai-websocket-url`, `disruptionai-websocket-api-id`
- `disruptionai-frontend-url`, `disruptionai-frontend-bucket`, `disruptionai-distribution-id`


### Phase 2: Seed DynamoDB Tables

After database tables are created, load mock ERP data:

```bash
# Activate Python virtual environment
source /tmp/disruptionai-venv/bin/activate

# Set region
export AWS_REGION=us-east-1

# Seed all 6 ERP tables (orders, capacity, manpower, materials, customers, tracker)
erp-data-mcp-seed
```

**Verification**:
```bash
# Confirm orders loaded (expect 40+ items: 20 Florida + 20 Ohio)
aws dynamodb scan --table-name disruptionai-orders --select COUNT

# Confirm capacity loaded
aws dynamodb scan --table-name disruptionai-capacity --select COUNT

# Confirm customers loaded
aws dynamodb scan --table-name disruptionai-customers --select COUNT
```

### Phase 3: Register MCP Servers on AgentCore Gateway

Register the ERP Data MCP and Audit MCP servers as FastMCP services on AgentCore Gateway. These become HTTP/SSE endpoints that agents call through the gateway.

**ERP Data MCP Registration**:
- Server Name: `erp-data-mcp`
- Entry Point: `erp_data_mcp.server`
- Gateway Route: `/mcp/erp-data`
- Environment Variables: All `DYNAMODB_TABLE_*` values from Phase 1 outputs

**Audit MCP Registration**:
- Server Name: `audit-mcp`
- Entry Point: `audit_mcp.server`
- Gateway Route: `/mcp/audit`
- Environment Variables: `DYNAMODB_TABLE_AUDIT` from Phase 1 outputs

**Note**: The exact registration commands depend on the AgentCore Gateway CLI/API available at deployment time. Consult the AgentCore Gateway documentation for the `register-mcp-server` command syntax.

### Phase 4: Register Agents on AgentCore Managed Runtime

Register all 4 agents on Bedrock AgentCore. Each agent is a Python package deployed to AgentCore's managed runtime.

**Deployment order** (respects dependency chain):

| Order | Agent | Agent ID | Entry Point |
|-------|-------|----------|-------------|
| 1 | Impact Assessment | `impact-assessment-agent` | `impact_assessment_agent.agent` |
| 2 | Capacity & Optimization | `capacity-optimization-agent` | `capacity_optimization_agent.agent` |
| 3 | Constraint Matching | `constraint-matching-agent` | `constraint_matching_agent.agent` |
| 4 | Orchestrator | `orchestrator-agent` | `orchestrator_agent.agent` |

**Per-agent registration**:
1. Package agent source code (zip or directory)
2. Register with AgentCore via CDK or CLI
3. Configure environment variables (model ID, gateway URL, agent IDs)
4. Attach IAM role with Bedrock invoke + CloudWatch permissions
5. Bind MCP tools via AgentCore Gateway routes

**Environment variables per agent**:

| Variable | Value |
|----------|-------|
| BEDROCK_MODEL_ID | `us.anthropic.claude-4-5-haiku-20250514-v1:0` |
| MCP_GATEWAY_URL | AgentCore Gateway endpoint (from registration) |
| LOG_LEVEL | `INFO` |

Orchestrator additionally needs:
| Variable | Value |
|----------|-------|
| IMPACT_ASSESSMENT_AGENT_ID | Agent ID from step 1 |
| CAPACITY_OPTIMIZATION_AGENT_ID | Agent ID from step 2 |
| CONSTRAINT_MATCHING_AGENT_ID | Agent ID from step 3 |
| AUDIT_MCP_URL | Gateway route for audit MCP |

**Verification**:
```bash
# Test each agent responds (replace with actual AgentCore CLI)
# Example: invoke agent with a simple health-check prompt
aws bedrock invoke-agent --agent-id impact-assessment-agent --input-text "health check"
```

### Phase 5: Connect WebSocket API to Orchestrator

The WebSocket Lambda handler (deployed in Phase 1) needs to be updated to route `sendMessage` events to the Orchestrator Agent via AgentCore.

**Steps**:
1. Update Lambda handler to invoke Orchestrator Agent on `sendMessage` route
2. Configure Lambda environment variable: `ORCHESTRATOR_AGENT_ID`
3. Add IAM permission for Lambda to invoke AgentCore agent
4. Redeploy Lambda with updated code

**Verification**:
```bash
# Test WebSocket connection
wscat -c wss://<api-id>.execute-api.us-east-1.amazonaws.com/prod
> {"action": "sendMessage", "data": "hello"}
```

### Phase 6: Deploy Frontend

Upload the built React SPA to S3 and invalidate CloudFront cache:

```bash
# Build frontend (if not already built)
cd frontend-spa
npm run build

# Get bucket name and distribution ID from CDK outputs
BUCKET=$(aws cloudformation describe-stacks --stack-name DisruptionAI-Frontend \
  --query "Stacks[0].Outputs[?ExportName=='disruptionai-frontend-bucket'].OutputValue" \
  --output text)

DIST_ID=$(aws cloudformation describe-stacks --stack-name DisruptionAI-Frontend \
  --query "Stacks[0].Outputs[?ExportName=='disruptionai-distribution-id'].OutputValue" \
  --output text)

# Upload to S3
aws s3 sync dist/ s3://$BUCKET --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
```

**Verification**:
```bash
# Get frontend URL
FRONTEND_URL=$(aws cloudformation describe-stacks --stack-name DisruptionAI-Frontend \
  --query "Stacks[0].Outputs[?ExportName=='disruptionai-frontend-url'].OutputValue" \
  --output text)

echo "Frontend available at: $FRONTEND_URL"

# Verify HTTPS and security headers
curl -I $FRONTEND_URL
# Expect: content-security-policy, strict-transport-security, x-content-type-options, x-frame-options
```

---

## Post-Deployment Verification

### Smoke Test Checklist

| # | Test | Command / Action | Expected Result |
|---|------|-----------------|-----------------|
| 1 | DynamoDB tables accessible | `aws dynamodb list-tables` | 7 `disruptionai-*` tables |
| 2 | Seed data present | `aws dynamodb scan --table-name disruptionai-orders --select COUNT` | 40+ items |
| 3 | CloudWatch log groups exist | `aws logs describe-log-groups --log-group-name-prefix /disruptionai` | 7 log groups |
| 4 | WebSocket connects | `wscat -c wss://<api-id>.execute-api.us-east-1.amazonaws.com/prod` | Connected |
| 5 | Frontend loads | Open `https://<cloudfront-domain>` in browser | React SPA renders |
| 6 | Security headers present | `curl -I https://<cloudfront-domain>` | CSP, HSTS, X-Frame-Options |
| 7 | Agent responds | Send message via WebSocket | Orchestrator streams response |
| 8 | Audit trail writes | Check DynamoDB audit table after agent interaction | Audit entries present |
| 9 | CloudWatch logs flowing | Check log groups after agent interaction | Log entries in all groups |
| 10 | Dashboard populated | Open CloudWatch > Dashboards > DisruptionAI-Overview | Metrics visible |

### End-to-End Workflow Test

1. Open frontend URL in browser
2. Verify WebSocket connection indicator shows "Connected"
3. Type: "A tornado is approaching our Florida plant. What should we do?"
4. Verify Orchestrator responds with disruption alert and at-risk order count
5. Confirm to trigger workflow
6. Verify Round 1 executes (Impact Assessment + Capacity Analysis in parallel)
7. Verify priority classification appears (P1/P2/P3 distribution)
8. Verify capacity analysis appears with bottleneck identification
9. Proceed through delay candidates (approve/reject)
10. Proceed through constraint matching (order-by-order approval)
11. Verify audit trail in side panel shows all decisions
12. Verify capacity tracker updates after each decision

---

## Rollback Procedure

### Full Rollback (Destroy All Resources)

```bash
cd infrastructure

# Empty S3 buckets first (CDK autoDeleteObjects handles this)
npx cdk destroy --all --force
```

### Partial Rollback (Per-Stack)

```bash
# Destroy in reverse dependency order
npx cdk destroy DisruptionAI-Frontend
npx cdk destroy DisruptionAI-WebSocket
npx cdk destroy DisruptionAI-IAM
npx cdk destroy DisruptionAI-Monitoring
npx cdk destroy DisruptionAI-Database
```

**Note**: All DynamoDB tables have `removalPolicy: DESTROY` and S3 buckets have `autoDeleteObjects: true`, so teardown is clean with no orphaned resources.

---

## Cost Estimate (MVP / Demo Usage)

| Service | Pricing Model | Estimated Monthly Cost |
|---------|--------------|----------------------|
| DynamoDB (7 tables) | On-Demand, minimal reads/writes | < $1 |
| CloudFront | Free tier (1 TB transfer) | $0 |
| S3 (frontend hosting) | Minimal storage | < $1 |
| API Gateway WebSocket | Per-message pricing | < $1 |
| Lambda (WebSocket handler) | Free tier (1M requests) | $0 |
| CloudWatch Logs | 5 GB free tier | < $1 |
| Bedrock (Claude 4.5 Haiku) | Per-token pricing | ~$5-20 (usage dependent) |
| AgentCore | Per-invocation pricing | ~$5-15 (usage dependent) |
| **Total (demo usage)** | | **~$10-40/month** |

**Note**: Costs are dominated by Bedrock LLM inference. Demo usage with occasional workflow runs stays well under $50/month. No always-on compute (ECS/Fargate) since agents run on AgentCore managed runtime.

---

## Security Checklist (Pre-Production)

| # | Check | SECURITY Rule | Status |
|---|-------|--------------|--------|
| 1 | DynamoDB encryption at rest enabled | SECURITY-01 | Verified (AWS-managed) |
| 2 | All connections use TLS 1.2+ | SECURITY-01 | Verified (SDK defaults) |
| 3 | CloudFront access logging enabled | SECURITY-02 | Verified (log bucket) |
| 4 | API Gateway access logging enabled | SECURITY-02 | Verified (CloudWatch) |
| 5 | All log groups have 90-day retention | SECURITY-14 | Verified (CDK config) |
| 6 | Security headers on all responses | SECURITY-04 | Verified (CloudFront policy) |
| 7 | IAM roles use least-privilege | SECURITY-06 | Verified (specific ARNs) |
| 8 | S3 public access blocked | SECURITY-09 | Verified (BlockPublicAccess.BLOCK_ALL) |
| 9 | No hardcoded credentials | SECURITY-12 | Verified (env vars + IAM roles) |
| 10 | Input validation on all endpoints | SECURITY-05 | Verified (Pydantic schemas) |
| 11 | Dependency vulnerability scan | SECURITY-10 | Run `pip-audit` and `npm audit` |
| 12 | Error responses sanitized | SECURITY-09 | Verified (fail-closed wrappers) |
