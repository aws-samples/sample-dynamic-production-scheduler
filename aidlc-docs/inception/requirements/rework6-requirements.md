# Requirements Document — Rework 6: Structured JSON Response Pipeline

## Intent Analysis Summary

- **User Request**: Rework the disruption workflow to use structured JSON responses instead of text parsing. Fix the response pipeline (orchestrator → AgentCore → Lambda proxy → browser) so the `ui` field survives end-to-end. All disruption components render from `msg.uiData` — no regex parsing.
- **Request Type**: Enhancement (backend + frontend pipeline rework)
- **Scope Estimate**: Multiple components — orchestrator agent, Lambda streaming proxy, frontend streaming/parsing/components
- **Complexity Estimate**: Moderate — well-scoped pipeline fix with clear boundaries

---

## Functional Requirements

### FR-01: Orchestrator `update_ui` Tool
The orchestrator agent shall register a local Python tool named `update_ui` (via Strands `@tool` decorator). When the LLM needs to send structured data to the frontend (phase transitions, order tables, capacity snapshots, approval requests), it calls `update_ui` with a typed payload instead of embedding data in its natural language response. The tool captures the payload and makes it available to `agentcore_server.py` for inclusion in the response envelope.

### FR-02: `update_ui` Payload Schema (Python)
The `update_ui` tool shall accept a Pydantic-validated payload with the following top-level fields:
- `phase` (str, optional): Current workflow phase identifier (e.g., `confirmation`, `round1_analysis`, `round1_complete`, `delay_optimization`, `constraint_funnel`, `summary`)
- `agents` (list, optional): Agent status objects `{name, status, summary}`
- `orders` (list, optional): Order objects `{orderId, product, customer, customerTier, value, dueDate, priority, risk, ...}`
- `capacity` (dict, optional): Capacity snapshot `{rollingMill, finishingLine, rawMaterial, manpower, overall}`
- `priorities` (dict, optional): Priority distribution `{P1, P2, P3}` with counts and values
- `approvalRequest` (dict, optional): Single order decision request `{orderId, product, customer, value, recommendation, options[]}`
- `totalOrders` (int, optional), `totalValue` (str, optional), `bottleneck` (str, optional)
- `complete` (bool, optional): Workflow completion signal

Invalid payloads shall be rejected by Pydantic validation and logged as warnings; the tool shall return an error message to the LLM so it can retry.

### FR-03: Orchestrator System Prompt Update
The orchestrator's system prompt shall be updated to instruct the LLM to call `update_ui` whenever it produces data the frontend needs to render. The prompt shall include:
- When to call `update_ui` (phase transitions, after sub-agent results, before approval requests)
- Schema examples for each phase (round1 results, delay candidates, funnel orders, summary)
- Instruction that the LLM's text response is purely for the chat display — all structured data goes through the tool

### FR-04: `agentcore_server.py` Envelope Construction
The `agentcore_server.py` `invoke()` function shall:
1. Run the agent as before
2. Collect the `update_ui` tool call results (accumulated during the agent's execution)
3. Merge them into a single `ui` dict (last-write-wins for scalar fields, concatenate for list fields)
4. Return `{"result": <LLM text>, "ui": <merged ui dict>, "session_id": <id>}`
5. Remove the `json_extractor.py` import and usage — no more regex extraction of LLM text

### FR-05: Delete `json_extractor.py`
The file `orchestrator-agent/src/orchestrator_agent/json_extractor.py` shall be deleted. All server-side regex extraction of LLM text is replaced by the `update_ui` tool-call approach.

### FR-06: Lambda Streaming Proxy — Envelope Passthrough
The Lambda streaming proxy (`infrastructure/streaming-proxy/index.mjs`) shall be updated to:
1. Buffer the AgentCore SSE response stream (instead of raw piping)
2. Parse the accumulated response to extract the JSON envelope `{result, ui, session_id}`
3. Forward the complete envelope as a single JSON response to the browser
4. Set `Content-Type: application/json` (not `text/event-stream`)
5. Preserve `X-Session-Id` header from the envelope's `session_id`
6. Validate that the `ui` field is valid JSON and strip unexpected top-level keys before forwarding (security: SECURITY-05 compliance)

### FR-07: Frontend `streaming.ts` — Simplified Response Handling
The `handleCompleteResponse()` function in `frontend-spa/src/lib/streaming.ts` shall be simplified to:
1. Parse the response as JSON
2. Extract `result` (display text), `ui` (structured data), `session_id`
3. Attach `uiData` to the chat message
4. Call `parseResponse(content, uiData)`
5. Remove all fallback paths: double-encoded string unwrapping, nested envelope detection, `extractStructuredJson()`, `extractUiFromText()`, and the client-side regex extraction functions

### FR-08: Frontend `responseParser.ts` — Remove Regex Extraction
The `responseParser.ts` module shall be refactored to:
1. Consume `uiData` (from the `ui` field) as the sole source of structured data
2. Remove all regex-based phase detection (`PHASE_PATTERNS`), agent extraction, capacity extraction, order table parsing, and approval request extraction
3. Keep only the store-update logic: map `uiData` fields to Zustand store actions (`setDisruptionPhase`, `setDisruptionAgentStatus`, `setDisruptionCapacityResults`, etc.)
4. If `uiData` is null/undefined, do nothing (show raw text as markdown in chat)

### FR-09: Frontend UI Schema (TypeScript)
A TypeScript interface `UiPayload` shall be defined matching the Python Pydantic model (FR-02). All disruption components shall import and use this type. The interface shall be in `frontend-spa/src/types/index.ts` or a dedicated `frontend-spa/src/types/ui.ts`.

### FR-10: Disruption Components — Render from `msg.uiData`
All disruption page components shall render exclusively from `msg.uiData`:
- **Round1SplitView**: Read `uiData.phase`, `uiData.agents`, `uiData.orders`, `uiData.capacity`, `uiData.priorities` — remove all regex checks on `m.content`
- **DelayCardQueue**: Read `uiData.approvalRequest` and `uiData.orders` — remove `extractApprovalRequests()` regex fallback
- **ConstraintFunnelView**: Read `uiData.approvalRequest` and `uiData.orders` — remove regex fallback
- **Round1ResultsCard**: Read `uiData.orders`, `uiData.capacity`, `uiData.priorities` — remove text parsing
- **KanbanBoard**: No changes needed (already reads from store)

### FR-11: Backward Compatibility — Non-Disruption Chat
The general chat view (AI Assistant) does not use the `ui` field. Non-disruption messages shall continue to display as markdown text. The `ui` field will simply be absent/empty for non-disruption responses.

---

## Non-Functional Requirements

### NFR-01: Schema Validation
The `update_ui` tool shall validate payloads with Pydantic on the Python side. The frontend shall use the TypeScript `UiPayload` interface for compile-time type safety. Runtime validation on the frontend is not required (trusted source).

### NFR-02: Performance
Buffering the AgentCore response in the Lambda proxy adds latency equal to the full response generation time (no incremental streaming). This is acceptable since the current implementation already buffers the full response in `streaming.ts` before processing.

### NFR-03: Security Baseline Compliance
- **SECURITY-05** (Input Validation): Lambda proxy shall validate `ui` field is valid JSON and strip unexpected top-level keys before forwarding
- **SECURITY-09** (Error Sanitization): Error responses from the proxy shall not leak internal AgentCore details
- **SECURITY-12** (Least Privilege): No new IAM permissions required — proxy already has AgentCore invoke permission
- No new API endpoints introduced

### NFR-04: Observability
The Lambda proxy shall log: response buffer size, whether `ui` field was present, and any parse errors. The orchestrator shall log each `update_ui` tool call with the payload phase field.

### NFR-05: Testability
- Python: Unit tests for `update_ui` tool with valid/invalid payloads
- Python: Unit tests for `agentcore_server.py` envelope construction with mocked agent
- TypeScript: Unit tests for simplified `handleCompleteResponse()` with sample envelopes
- TypeScript: Unit tests for refactored `parseResponse()` with `uiData` input

---

## Extension Compliance

| Extension | Enabled | Status |
|-----------|---------|--------|
| Security Baseline | Yes | Compliant — SECURITY-05/09/12 addressed in NFR-03 |

---

## Files Affected

| File | Change Type | Description |
|------|------------|-------------|
| `orchestrator-agent/src/orchestrator_agent/agent.py` | MODIFY | Register `update_ui` tool, capture results |
| `orchestrator-agent/src/orchestrator_agent/agentcore_server.py` | MODIFY | Collect `update_ui` results, build envelope, remove json_extractor |
| `orchestrator-agent/src/orchestrator_agent/json_extractor.py` | DELETE | Replaced by tool-call approach |
| `orchestrator-agent/src/orchestrator_agent/prompts/system_prompt.py` | MODIFY | Add `update_ui` usage instructions |
| `orchestrator-agent/src/orchestrator_agent/models/schemas.py` | MODIFY | Add `UiPayload` Pydantic model |
| `infrastructure/streaming-proxy/index.mjs` | MODIFY | Buffer response, parse envelope, forward JSON |
| `frontend-spa/src/lib/streaming.ts` | MODIFY | Simplify `handleCompleteResponse()`, remove regex functions |
| `frontend-spa/src/lib/responseParser.ts` | MODIFY | Remove regex extraction, consume `uiData` only |
| `frontend-spa/src/types/index.ts` | MODIFY | Add `UiPayload` TypeScript interface |
| `frontend-spa/src/components/disruption/Round1SplitView.tsx` | MODIFY | Render from `uiData`, remove regex checks |
| `frontend-spa/src/components/disruption/DelayCardQueue.tsx` | MODIFY | Render from `uiData`, remove regex fallback |
| `frontend-spa/src/components/disruption/ConstraintFunnelView.tsx` | MODIFY | Render from `uiData`, remove regex fallback |
| `frontend-spa/src/components/disruption/Round1ResultsCard.tsx` | MODIFY | Render from `uiData`, remove text parsing |
| `orchestrator-agent/tests/test_agent.py` | MODIFY | Add `update_ui` tool tests |
| `frontend-spa/src/lib/__tests__/streaming.test.ts` | CREATE | Tests for simplified response handling |
