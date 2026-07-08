# Code Generation Plan — Rework 6: Structured JSON Response Pipeline

## Overview
15 steps across 3 parallel streams. Streams A and B have no dependencies on each other. Stream C depends on the `UiPayload` TypeScript interface (Step 9) but the component updates (Steps 12-15) are independent of each other.

## Stream A: Orchestrator Backend (Python)
- [x] Step 1: Add `UiPayload` Pydantic model to `orchestrator-agent/src/orchestrator_agent/models/schemas.py` (FR-02)
- [x] Step 2: Create `update_ui` tool in `orchestrator-agent/src/orchestrator_agent/agent.py` with thread-local accumulator (FR-01)
- [x] Step 3: Update `orchestrator-agent/src/orchestrator_agent/agentcore_server.py` — collect `update_ui` results, build envelope, remove `json_extractor` import (FR-04)
- [x] Step 4: Update `orchestrator-agent/src/orchestrator_agent/prompts/system_prompt.py` — add `update_ui` usage instructions (FR-03)
- [x] Step 5: Delete `orchestrator-agent/src/orchestrator_agent/json_extractor.py` (FR-05)
- [x] Step 6: Update `orchestrator-agent/tests/test_agent.py` — add `update_ui` tool tests (NFR-05)

## Stream B: Lambda Streaming Proxy (Node.js)
- [x] Step 7: Rewrite `infrastructure/streaming-proxy/index.mjs` — buffer AgentCore response, parse envelope, forward JSON with `ui` field validation (FR-06, NFR-03)

## Stream C: Frontend (TypeScript/React)
- [x] Step 8: Add `UiPayload` TypeScript interface to `frontend-spa/src/types/index.ts` (FR-09)
- [x] Step 9: Simplify `frontend-spa/src/lib/streaming.ts` — strip `handleCompleteResponse()` to minimal JSON parse, remove `extractStructuredJson()`, `extractUiFromText()` (FR-07)
- [x] Step 10: Refactor `frontend-spa/src/lib/responseParser.ts` — remove all regex extraction, consume `uiData` only (FR-08)
- [x] Step 11: Update `frontend-spa/src/components/disruption/Round1SplitView.tsx` — render from `uiData` (FR-10)
- [x] Step 12: Update `frontend-spa/src/components/disruption/Round1ResultsCard.tsx` — render from `uiData` (FR-10)
- [x] Step 13: Update `frontend-spa/src/components/disruption/DelayCardQueue.tsx` — render from `uiData` (FR-10)
- [x] Step 14: Update `frontend-spa/src/components/disruption/ConstraintFunnelView.tsx` — render from `uiData` (FR-10)

## Parallelization Strategy
- **Wave 1** (parallel): Stream A (Steps 1-6) + Stream B (Step 7) + Stream C Step 8 (UiPayload interface)
- **Wave 2** (parallel after Wave 1): Stream C Steps 9-10 (streaming.ts + responseParser.ts)
- **Wave 3** (parallel after Wave 2): Stream C Steps 11-14 (4 disruption components)
