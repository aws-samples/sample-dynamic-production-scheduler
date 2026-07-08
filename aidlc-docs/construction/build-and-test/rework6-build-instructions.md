# Build Instructions — Rework 6: Structured JSON Response Pipeline

## Prerequisites
- Python 3.11+ with pip
- Node.js 18+ with npm
- AWS CDK CLI (for Lambda bundling)

## Build Steps

### 1. Orchestrator Agent (Python)

```bash
cd orchestrator-agent
pip install -e ".[dev]"
```

Verify `json_extractor.py` is deleted:
```bash
ls src/orchestrator_agent/json_extractor.py  # Should return "No such file"
```

Verify `update_ui` tool is registered:
```bash
python -c "from orchestrator_agent.agent import PYTHON_TOOLS; print([t.__name__ for t in PYTHON_TOOLS])"
# Should include 'update_ui'
```

### 2. Lambda Streaming Proxy (Node.js)

```bash
cd infrastructure/streaming-proxy
npm install  # If package.json exists, otherwise no deps needed
```

Verify the proxy no longer imports `pipeline` or `Readable`:
```bash
grep -c "pipeline\|Readable" index.mjs  # Should return 0
```

### 3. Frontend SPA (TypeScript/React)

```bash
cd frontend-spa
npm install
npx tsc --noEmit  # Type check — should pass with 0 errors (ignore pre-existing dashboardData warnings)
npm run build     # Production build
```

### 4. CDK Infrastructure (Lambda rebundle)

```bash
cd infrastructure
npx cdk synth     # Synthesize — picks up new streaming-proxy/index.mjs
```

## Build Artifacts
- `orchestrator-agent/` — Python package with `update_ui` tool
- `infrastructure/streaming-proxy/index.mjs` — Updated Lambda handler
- `frontend-spa/dist/` — Production frontend build
- `infrastructure/cdk.out/` — CDK synthesis output

## Troubleshooting

### Import error: `json_extractor`
If any module still imports `json_extractor`, grep for it:
```bash
grep -r "json_extractor" orchestrator-agent/
```
The only reference should be in test files (if any) — remove them.

### TypeScript errors in disruption components
If `UiPayload` type errors appear, ensure `frontend-spa/src/types/index.ts` has the Rework 6 interfaces at the bottom of the file.
