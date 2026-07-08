# Deployment Plan — Rework 7

## Deployment Order

### Step 1: Deploy Lambda Proxy Update
The REST proxy (`DisruptionAI-RestProxy`) passes the `ui` field through without filtering — no CDK deploy needed for the proxy. The `streaming-proxy/index.mjs` allowlist was updated as a safety measure but is not on the critical path since the frontend uses the REST proxy.

Skip this step unless you want to redeploy the REST proxy for other reasons:
```bash
cd infrastructure
npx cdk deploy DisruptionAI-RestProxy --require-approval never
```

### Step 2: Redeploy Orchestrator Agent
```bash
cd infrastructure
python scripts/redeploy_agents.py --agent orchestrator_agent
```
Updates the Pydantic schema and system prompt. The agent will start emitting `capacityImpact` and `transferOrders` fields in `update_ui` calls.

### Step 3: Deploy Frontend
```bash
cd frontend-spa
npm run build
aws s3 sync dist/ s3://<frontend-bucket-name> --delete
aws cloudfront create-invalidation --distribution-id <distribution-id> --paths "/*"
```

### Step 4: Verify
1. Open the frontend URL
2. Start a disruption workflow
3. Verify the three-column layout appears during delay optimization
4. Verify Transfer Negotiation shows Incoming/Outgoing tabs
5. Verify Capacity Summary step appears after constraint funnel

## Rollback
- Frontend: Redeploy previous S3 build
- Lambda proxy: `cdk deploy McpLambdaStack` with reverted `index.mjs`
- Orchestrator: Redeploy with previous agent code

## No-Impact Components
- Impact Assessment Agent — unchanged
- Capacity & Optimization Agent — unchanged
- Constraint Matching Agent — unchanged
- ERP Data MCP — unchanged
- Audit MCP — unchanged
- DynamoDB tables — unchanged
- Cognito — unchanged
- WebSocket API Gateway — unchanged
