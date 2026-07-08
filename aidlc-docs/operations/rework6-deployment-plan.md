# Deployment Plan — Rework 6: Structured JSON Response Pipeline

## Overview

Deploy the structured JSON response pipeline across 3 layers: orchestrator agent, Lambda streaming proxy, and frontend SPA. No new AWS resources — code-only updates to existing components.

## Pre-Deployment Checklist

- [ ] TypeScript type check passes (`cd frontend-spa && npx tsc --noEmit`)
- [ ] Orchestrator tests pass locally (if Python 3.11 available)
- [ ] AWS CLI configured for account, region `us-east-1`
- [ ] Current system is stable (all 4 agents READY on AgentCore Runtime)
- [ ] `json_extractor.py` is deleted from the orchestrator source

## Deployment Sequence

### Step 1: Redeploy Orchestrator Agent

The orchestrator has 4 modified files + 1 deleted file. Redeploy via the existing script:

```bash
# Ensure orchestrator source is up to date
# Modified: agent.py, agentcore_server.py, models/schemas.py, prompts/system_prompt.py
# Deleted: json_extractor.py

ACCOUNT_ID=YOUR_ACCOUNT_ID python3 infrastructure/scripts/redeploy_agents.py
```

This re-packages the orchestrator source, uploads to S3, and triggers `update_agent_runtime`. Wait for READY status.

**Verify**: The orchestrator now has the `update_ui` tool registered. Check CloudWatch logs for `"update_ui called"` entries after a test invocation.

**Note**: Sub-agents (impact-assessment, capacity-optimization, constraint-matching) are unchanged — no redeployment needed.

### Step 2: Redeploy Lambda Streaming Proxy

The Lambda streaming proxy (`infrastructure/streaming-proxy/index.mjs`) changed from SSE piping to JSON buffering. Redeploy via CDK:

```bash
cd infrastructure
npm run build
npx cdk deploy DisruptionAI-RestProxy --require-approval never
```

**Verify**: The Lambda now returns `Content-Type: application/json` instead of `text/event-stream`.

```bash
# Quick test — should return JSON with {result, ui, session_id}
curl -X POST YOUR_REST_PROXY_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "hello", "sessionId": "deploy-test-rework6"}' \
  2>/dev/null | python3 -m json.tool | head -5
```

Expected: `{"result": "...", "ui": {...}, "session_id": "..."}` — not SSE `data:` lines.

### Step 3: Build and Deploy Frontend

```bash
cd frontend-spa
npm install
npm run build

# Deploy to S3
aws s3 sync dist/ s3://YOUR_SITE_BUCKET_NAME --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

**Verify**: Open the CloudFront URL. The disruption workflow should render structured data in UI components (not raw markdown with embedded JSON blocks).

### Step 4: End-to-End Validation

1. Open the frontend at the CloudFront URL
2. Sign in with Cognito credentials
3. Navigate to the Disruption page
4. Select a plant and start a disruption response
5. Verify each phase:
   - **Confirmation**: Orchestrator asks to confirm → UI shows confirmation card
   - **Round 1**: Sub-agents run → results render in structured card (priorities, capacity bars, order table)
   - **Delay Optimization**: Delay candidates appear as cards with Approve/Reject buttons
   - **Constraint Funnel**: Orders appear with 4-layer funnel results and decision buttons
   - **Summary**: Workflow completes, navigates to dashboard

6. Check browser DevTools Network tab:
   - Response from Lambda should be `Content-Type: application/json`
   - Response body should contain `"ui": {...}` with structured data
   - No `data:` SSE lines in the response

7. Check CloudWatch logs:
   - Orchestrator: Look for `"update_ui called"` log entries with phase fields
   - Lambda proxy: Look for `"UI field present: keys=..."` log entries
   - No `json_extractor` references in any logs

## Rollback Plan

If the deployment fails at any step:

### Step 1 Rollback (Orchestrator)
- Revert the orchestrator source to the pre-rework6 version
- Re-run `redeploy_agents.py` to restore the old code
- The old `json_extractor.py` will be restored and the `update_ui` tool removed

### Step 2 Rollback (Lambda Proxy)
- Revert `infrastructure/streaming-proxy/index.mjs` to the SSE piping version
- Re-run `npx cdk deploy DisruptionAI-RestProxy`
- The proxy will resume piping SSE streams

### Step 3 Rollback (Frontend)
- Revert the frontend source to the pre-rework6 version
- Rebuild and redeploy to S3 + CloudFront
- The frontend will resume regex-based text parsing

**Important**: Steps 1 and 2 must be rolled back together — the frontend expects the `ui` field from the proxy, which requires the orchestrator's `update_ui` tool. Rolling back only one side will break the pipeline.

## Post-Deployment Monitoring

- **Orchestrator CloudWatch**: Check for `update_ui` tool call frequency and any validation failures
- **Lambda CloudWatch**: Check for `"UI field present"` vs `"UI field not present"` log ratio
- **Frontend**: Monitor browser console for `"UI data from envelope"` log messages
- **Error rate**: Compare pre/post deployment error rates in CloudWatch metrics
