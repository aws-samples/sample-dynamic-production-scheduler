# Rework Cycle 4 — Build & Test Instructions

## Test Results Summary

| Component | Tests | Result |
|-----------|-------|--------|
| Frontend SPA | 24 | All passed |
| ERP Data MCP | 65 | All passed |
| Orchestrator Agent | 64 | All passed |
| Capacity Optimization Agent | 98 | All passed |
| CDK Synth (Cognito + RestProxy) | — | Passed |
| Frontend Build (tsc + vite) | — | Passed |

Total: 251 tests passed, 0 failures.

## Deployment Steps

### Step 1: Deploy Cognito Stack (custom:plant attribute)
```bash
cd infrastructure
npx cdk deploy DisruptionAI-Cognito --require-approval never
```
Note: Adding a custom attribute to an existing User Pool is supported. Existing users will not have the attribute set — use the admin script in Step 5.

### Step 2: Deploy REST Proxy Stack (plant passthrough)
```bash
npx cdk deploy DisruptionAI-RestProxy --require-approval never
```

### Step 3: Re-seed DynamoDB (Florida plant data + Ohio tuning)
```bash
cd erp-data-mcp
source .venv/bin/activate
erp-data-mcp-seed
```
This loads the updated seed data including Florida plant capacity, manpower, and materials, plus the tuned Ohio utilization rates.

### Step 4: Redeploy Orchestrator Agent (plant-scoped prompt)
```bash
ACCOUNT_ID=058264253938 python3 infrastructure/scripts/redeploy_agents.py
```
This updates the orchestrator with the new `get_system_prompt(plant=...)` and `agentcore_server.py` plant extraction.

### Step 5: Set Plant Attributes on Users
```bash
cd infrastructure/scripts
python3 set_user_plant.py --email miami-planner@example.com --plant Florida
python3 set_user_plant.py --email ohio-planner@example.com --plant Ohio
```
Replace email addresses with actual Cognito user emails.

### Step 6: Build and Deploy Frontend
```bash
cd frontend-spa
npm run build
aws s3 sync dist/ s3://disruptionai-frontend-058264253938 --delete
aws cloudfront create-invalidation --distribution-id E3KKSG60PFHFU --paths "/*"
```

### Step 7: Verify
1. Log in as Miami planner → should see "Miami Plant Operations" dashboard with Job Status and Efficiency views
2. Log in as Ohio planner → should see "Ohio Plant Operations" dashboard
3. Navigate between Dashboard / Chat / Transfers tabs
4. In Chat, trigger a disruption → notification banner should appear on Miami dashboard
5. Verify Ohio capacity shows ~82% Rolling Mill, ~80% Finishing Line utilization
