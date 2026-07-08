# Rework Cycle 3 — Unit Test Instructions

## Backend Agent Unit Tests

### Test Scope per Agent

Each agent has tests covering config loading, schema validation, and agent logic.

### Orchestrator Agent

```bash
cd orchestrator-agent
/opt/homebrew/bin/python3.11 -m pytest tests/ -v
```

Key test areas for Rework Cycle 3 changes:
- `test_config.py` — verify `retry_delay_seconds` defaults to 30
- `test_agent.py` — verify `max_tokens=16384` in model config
- `test_session.py` — session state transitions
- `test_schemas.py` — schema validation

### Impact Assessment Agent

```bash
cd impact-assessment-agent
/opt/homebrew/bin/python3.11 -m pytest tests/ -v
```

Key test areas:
- `test_agent.py` — verify `max_tokens=8192`, data staging tool registration
- `test_scoring.py` — scoring logic with staged data pattern
- `test_config.py` — config field validation
- `test_schemas.py` — schema validation

### Capacity Optimization Agent

```bash
cd capacity-optimization-agent
/opt/homebrew/bin/python3.11 -m pytest tests/ -v
```

Key test areas:
- `test_agent.py` — verify `max_tokens=8192`, data staging tool registration
- `test_capacity.py` — capacity snapshot with staged data pattern
- `test_config.py` — config field validation
- `test_schemas.py` — schema validation

### Constraint Matching Agent

```bash
cd constraint-matching-agent
/opt/homebrew/bin/python3.11 -m pytest tests/ -v
```

Key test areas:
- `test_agent.py` — verify `max_tokens=8192`, data staging tool registration
- `test_funnel.py` — funnel logic with plant-agnostic parameter names
- `test_config.py` — config field validation
- `test_schemas.py` — schema validation

### Expected Results
- All tests pass with 0 failures
- No deprecation warnings from Strands SDK

## Frontend Unit Tests

```bash
cd frontend-spa
npm run test
```

### Test Files
- `src/test/store.test.ts` — Zustand store actions (phase updates, agent status, order history)
- `src/test/websocket.test.ts` — WebSocket message parsing (stream_token, phase_update, agent_switch)
- `src/test/components.test.tsx` — Component rendering (ChatMessage, SubAgentStatus, OrderHistory)

### Expected Results
- All tests pass
- No TypeScript compilation errors
- Components render without runtime errors

## Running All Tests

From workspace root:

```bash
# Backend (all 4 agents)
for agent in orchestrator-agent impact-assessment-agent capacity-optimization-agent constraint-matching-agent; do
  echo "=== Testing $agent ==="
  (cd $agent && /opt/homebrew/bin/python3.11 -m pytest tests/ -v)
done

# Frontend
(cd frontend-spa && npm run test)
```
