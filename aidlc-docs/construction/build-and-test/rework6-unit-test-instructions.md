# Unit Test Instructions — Rework 6

## Orchestrator Agent Tests

```bash
cd orchestrator-agent
python -m pytest tests/test_agent.py -v --tb=short
```

### Expected Results
- All existing tests (sub-agent tools, session tools, run_agent, create_agent, session cache) should pass
- 5 new `TestUpdateUiTool` tests should pass:
  - `test_update_ui_valid_phase` — stores payload with phase field
  - `test_update_ui_accumulates_multiple` — multiple calls accumulate
  - `test_update_ui_reset_clears` — reset clears previous payloads
  - `test_update_ui_with_orders` — orders list validates correctly
  - `test_update_ui_with_approval_request` — approval request validates

### Full Agent Test Suite
```bash
cd orchestrator-agent
python -m pytest tests/ -v --tb=short
```

## Frontend Type Check

```bash
cd frontend-spa
npx tsc --noEmit
```

### Expected Results
- 0 errors from rework6 changes
- Pre-existing warnings in `dashboardData.ts` are acceptable (unused imports)

## All Python Agent Tests

```bash
# Run all agent test suites to verify no regressions
cd erp-data-mcp && python -m pytest tests/ -v --tb=short
cd audit-mcp && python -m pytest tests/ -v --tb=short
cd impact-assessment-agent && python -m pytest tests/ -v --tb=short
cd capacity-optimization-agent && python -m pytest tests/ -v --tb=short
cd constraint-matching-agent && python -m pytest tests/ -v --tb=short
cd orchestrator-agent && python -m pytest tests/ -v --tb=short
```
