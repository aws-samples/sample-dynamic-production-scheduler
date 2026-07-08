# Build Instructions — Rework 7: Transfer Negotiation, Live Capacity Impact & Cross-Plant Dashboard Updates

## Prerequisites
- Node.js 18+ and npm installed
- Python 3.11+ with pip installed
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- AWS credentials configured for the target account

## 1. Frontend Build

```bash
cd frontend-spa
npm install
npm run build
```

Expected: Clean build with zero errors. The build output goes to `frontend-spa/dist/`.

Verify new components compile:
- `CapacityImpactPanel.tsx` — new component
- `CapacitySummaryStep.tsx` — new component
- `DisruptionPage.tsx` — three-column layout
- `PhaseStepper.tsx` — capacity_summary step
- `TransferNegotiationView.tsx` — full rewrite with tabs
- `JobStatusView.tsx` — Transferred In badges

## 2. Backend Build — Orchestrator Agent

```bash
cd orchestrator-agent
pip install -e ".[dev]"
```

Verify the Pydantic models import correctly:
```bash
python -c "from orchestrator_agent.models.schemas import UiPayload, UiCapacityImpact, UiTransferOrder; print('Schema imports OK')"
```

## 3. Infrastructure — Lambda Proxy

```bash
cd infrastructure
npm install
npx cdk synth
```

Verify `streaming-proxy/index.mjs` has `capacityImpact` and `transferOrders` in the `ALLOWED_UI_KEYS` array.

## 4. CDK Deploy (if deploying)

```bash
cd infrastructure
npx cdk deploy --all --require-approval never
```

Only the McpLambdaStack needs redeployment (Lambda proxy code change). No new stacks.

## 5. Frontend Deploy (if deploying)

```bash
cd frontend-spa
npm run build
aws s3 sync dist/ s3://<frontend-bucket-name> --delete
aws cloudfront create-invalidation --distribution-id <distribution-id> --paths "/*"
```

## 6. Orchestrator Agent Redeploy

```bash
cd infrastructure
python scripts/redeploy_agents.py --agent orchestrator_agent
```

Only the orchestrator agent needs redeployment (schema + prompt changes). Other agents are unchanged.
