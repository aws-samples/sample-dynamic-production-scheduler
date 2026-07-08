# Implementation Plan: Deterministic JSON Pipeline

## Overview

Rework the orchestrator response pipeline to replace LLM-driven JSON formatting with deterministic structured outputs. Sub-agents return validated Pydantic objects, the orchestrator builds UI payloads in Python, and the trailer/fallback extraction system is removed from all layers. Tasks are ordered by dependency: sub-agent models → sub-agent server changes → orchestrator changes → proxy/frontend cleanup.

## Tasks

- [x] 1. Define sub-agent structured output Pydantic models
  - [x] 1.1 Create `ImpactAssessmentOutput` model in `impact-assessment-agent/src/impact_assessment_agent/models/schemas.py`
    - Add `ImpactAssessmentOutput(BaseModel)` with `scored_orders: list[ScoredOrder]`, `priority_summary: PrioritySummary`, `total_value: float`, `summary_text: str`
    - Reuse existing `ScoredOrder` and `PrioritySummary` models already in that file
    - _Requirements: 1.1, 1.4_

  - [x] 1.2 Create `CapacityOptimizationOutput` and helper models in `capacity-optimization-agent/src/capacity_optimization_agent/models/schemas.py`
    - Add `MachineUtilizationSummary(BaseModel)` with `machine_type`, `normal_utilization_pct`, `total_surplus_hours`
    - Add `DelayCandidateSummary(BaseModel)` with `order_id`, `product_family`, `customer_id`, `customer_tier`, `order_value`, `due_date`, `slack_days`, `freed_rolling_mill_hours`, `freed_finishing_line_hours`, `freed_material_tons`, `risk_level`, `trade_off_explanation`
    - Add `CapacityOptimizationOutput(BaseModel)` with `utilization`, `manpower_utilization_pct`, `material_utilization_pct`, `bottleneck`, `delay_candidates`, `surplus_summary`, `summary_text`
    - _Requirements: 1.2, 1.5_

  - [x] 1.3 Create `ConstraintMatchingOutput` and helper models in `constraint-matching-agent/src/constraint_matching_agent/models/schemas.py`
    - Add `FunnelLayerSummary(BaseModel)` with `layer`, `name`, `passed`, `detail`
    - Add `FunnelOrderSummary(BaseModel)` with `order_id`, `priority`, `product_family`, `customer_id`, `customer_tier`, `order_value`, `due_date`, `all_layers_passed`, `recommendation`, `recommendation_category`, `reasoning`, `layers`
    - Add `TransferSummary(BaseModel)` if not already present
    - Add `ConstraintMatchingOutput(BaseModel)` with `funnel_results`, `transfer_summary`, `summary_text`
    - _Requirements: 1.3, 1.6_

  - [ ]* 1.4 Write property test for sub-agent structured output schema conformance
    - **Property 1: Sub-agent structured output schema conformance**
    - Generate random valid ERP data inputs via Hypothesis strategies, run through scoring/capacity/funnel engines, validate output against respective Pydantic models
    - Test in each sub-agent's `tests/test_structured_output.py`
    - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 2. Wire structured_output_model into sub-agent Agent factories
  - [x] 2.1 Update Impact Assessment Agent `create_agent()` in `impact-assessment-agent/src/impact_assessment_agent/agent.py`
    - Add `structured_output_model=ImpactAssessmentOutput` to the `Agent()` constructor
    - Import `ImpactAssessmentOutput` from models.schemas
    - _Requirements: 1.4_

  - [x] 2.2 Update Capacity Optimization Agent `create_agent()` in `capacity-optimization-agent/src/capacity_optimization_agent/agent.py`
    - Add `structured_output_model=CapacityOptimizationOutput` to the `Agent()` constructor
    - Import `CapacityOptimizationOutput` from models.schemas
    - _Requirements: 1.5_

  - [x] 2.3 Update Constraint Matching Agent `create_agent()` in `constraint-matching-agent/src/constraint_matching_agent/agent.py`
    - Add `structured_output_model=ConstraintMatchingOutput` to the `Agent()` constructor
    - Import `ConstraintMatchingOutput` from models.schemas
    - _Requirements: 1.6_

- [x] 3. Update sub-agent AgentCore servers to return structured_output
  - [x] 3.1 Update `impact-assessment-agent/src/impact_assessment_agent/agentcore_server.py` invoke()
    - After `run_agent()`, extract structured output from agent result (check for `model_dump()` or parse JSON)
    - Include `structured_output` key in success response dict
    - On validation failure, return error response with descriptive message
    - _Requirements: 1.7, 1.8, 7.1_

  - [x] 3.2 Update `capacity-optimization-agent/src/capacity_optimization_agent/agentcore_server.py` invoke()
    - Same pattern: extract structured output, include in response, handle validation errors
    - _Requirements: 1.7, 1.8, 7.2_

  - [x] 3.3 Update `constraint-matching-agent/src/constraint_matching_agent/agentcore_server.py` invoke()
    - Same pattern: extract structured output, include in response, handle validation errors
    - _Requirements: 1.7, 1.8, 7.3_

  - [ ]* 3.4 Write property test for sub-agent response envelope
    - **Property 2: Sub-agent response envelope contains structured_output**
    - Generate random valid agent results, verify response dict contains `structured_output` key with non-empty dict
    - Test in each sub-agent's `tests/test_agentcore_server.py`
    - **Validates: Requirements 1.7, 7.1, 7.2, 7.3**

  - [ ]* 3.5 Write unit tests for validation error and failure edge cases
    - Test that validation failure returns error response without `structured_output` (Req 1.8)
    - Test that failed invocation returns error response without `structured_output` (Req 7.4)
    - _Requirements: 1.8, 7.4_

- [x] 4. Checkpoint — Sub-agent structured output complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Add capacityImpact to Capacity Optimization Agent tool returns
  - [x] 5.1 Add `_build_capacity_impact` helper in `capacity-optimization-agent/src/capacity_optimization_agent/agent.py`
    - Implement deterministic computation from `CapacityState` snapshot
    - Returns dict with `senderPlant` and `receiverPlant` objects, each with `name`, `rollingMill`, `finishingLine`, `overall` (each with `current` and `projected`)
    - _Requirements: 6.3, 6.4_

  - [x] 5.2 Update `process_delay_decision` tool to include `capacityImpact` in return value
    - Call `_build_capacity_impact` after delay application and include in JSON return
    - _Requirements: 6.1_

  - [x] 5.3 Update `apply_constraint_tool` to include `capacityImpact` in return value
    - Call `_build_capacity_impact` after constraint application and include in JSON return
    - _Requirements: 6.2_

  - [ ]* 5.4 Write property test for capacityImpact structure and determinism
    - **Property 11: capacityImpact structure from deterministic computation**
    - Generate random CapacityState snapshots via Hypothesis, verify structure has all required fields, verify calling twice produces identical results
    - Test in `capacity-optimization-agent/tests/test_capacity_impact.py`
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [x] 6. Update orchestrator sub-agent invocation to parse structured outputs
  - [x] 6.1 Add structured output accumulator to `orchestrator-agent/src/orchestrator_agent/agent.py`
    - Add `_structured_outputs: dict[str, dict] = {}` module-level dict
    - Add `_reset_structured_outputs()` and `_get_structured_outputs()` functions
    - _Requirements: 2.1, 8.1, 8.2_

  - [x] 6.2 Update `_invoke_sub_agent` in `orchestrator-agent/src/orchestrator_agent/agent.py`
    - Parse response body as JSON, extract `structured_output` field if present
    - Store in `_structured_outputs` accumulator keyed by agent name
    - Continue returning text summary to LLM for reasoning
    - Fall back gracefully if `structured_output` is missing
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ]* 6.3 Write property tests for accumulator extraction and text preservation
    - **Property 3: Orchestrator extracts and accumulates structured outputs**
    - Generate random response dicts with/without `structured_output`, verify accumulator state
    - **Property 13: Text summary returned alongside structured output**
    - Generate responses with both fields, verify both are preserved
    - Test in `orchestrator-agent/tests/test_invoke_helper.py`
    - **Validates: Requirements 2.1, 8.1, 8.2, 8.4**

- [x] 7. Implement deterministic UI assembly in orchestrator AgentCore server
  - [x] 7.1 Add `_build_ui_payload` function to `orchestrator-agent/src/orchestrator_agent/agentcore_server.py`
    - Pure function: takes `structured_outputs` dict and `phase` string, returns `ui` dict
    - Map Impact Assessment output → orders, priorities, totalOrders, totalValue
    - Map Capacity Optimization output → capacity, bottleneck
    - Map Constraint Matching output → transferOrders, approvalRequest with funnelResults
    - Handle round1_complete, delay_optimization, constraint_funnel, and summary phases
    - Return empty dict when no structured outputs present
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 5.3_

  - [x] 7.2 Update `invoke()` in `orchestrator-agent/src/orchestrator_agent/agentcore_server.py`
    - Call `_reset_structured_outputs()` at invocation start
    - After `run_agent()`, call `_build_ui_payload(_get_structured_outputs(), current_phase)`
    - Return `{"result": result.data, "ui": ui, "session_id": session_id}`
    - Remove calls to `_reset_ui_accumulator`, `_get_ui_payloads`, and all UI accumulator merge logic
    - Remove `_extract_ui_fallback` call and function
    - Remove base64 trailer embedding (`<!--UI_B64:...:UI_B64-->`)
    - Remove ASCII-only encoding (`encode("ascii", errors="ignore")`)
    - _Requirements: 2.1, 2.7, 4.1, 4.6, 5.1, 5.2, 5.3_

  - [ ]* 7.3 Write property tests for UI assembly
    - **Property 4: UI assembly determinism** — call `_build_ui_payload` twice with same args, assert identical results
    - **Property 5: Round 1 UI payload completeness** — verify all required fields present for valid IA+CO outputs
    - **Property 6: Delay optimization UI payload assembly** — verify approvalRequest and capacityImpact
    - **Property 7: Constraint funnel UI payload assembly** — verify approvalRequest with funnelResults
    - **Property 8: Summary UI payload assembly** — verify complete=true and transferOrders
    - **Property 10: Empty ui when no structured outputs** — verify empty dict for empty inputs
    - Test in `orchestrator-agent/tests/test_ui_assembly.py`
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.5, 2.6, 5.3**

  - [ ]* 7.4 Write property test for no trailers in result text
    - **Property 9: No trailers in orchestrator result text**
    - Generate random result strings, verify no `<!--UI_B64:` or `<!--UI_DATA:` substrings
    - **Property 17: Orchestrator response envelope structure** — verify exactly three top-level keys: result, ui, session_id
    - Test in `orchestrator-agent/tests/test_agentcore_server.py`
    - **Validates: Requirements 4.1, 2.7**

- [x] 8. Implement Round 1 parallel invocation via ThreadPoolExecutor
  - [x] 8.1 Add `_invoke_round1_parallel` function to `orchestrator-agent/src/orchestrator_agent/agentcore_server.py`
    - Use `concurrent.futures.ThreadPoolExecutor(max_workers=2)` to invoke IA and CO in parallel
    - Use existing `_invoke_sub_agent` helper for each call (preserves retry, error recording, structured output extraction)
    - Return dict mapping agent name to text result
    - Handle partial failure: if one agent fails, return results from the successful one plus error text
    - _Requirements: 13.1, 13.2, 13.4_

  - [x] 8.2 Update `invoke()` to detect Round 1 and dispatch parallel invocation
    - Detect round1 phase from `current_phase` or session state
    - Call `_invoke_round1_parallel` instead of relying on LLM tool calls for Round 1
    - Feed combined text results to the LLM for summary generation
    - Build `round1_complete` UI payload from both structured outputs
    - _Requirements: 13.1, 13.3_

  - [ ]* 8.3 Write unit tests for parallel invocation
    - Test both agents succeed: verify both structured outputs accumulated, UI payload complete
    - Test partial failure: verify successful agent's output preserved, error indicator present
    - Test that `_invoke_sub_agent` is used (preserves retry logic) — Req 13.2
    - Test in `orchestrator-agent/tests/test_parallel_invocation.py`
    - _Requirements: 13.1, 13.2, 13.4_

- [x] 9. Checkpoint — Orchestrator deterministic pipeline complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Remove update_ui tool and UI accumulator from orchestrator agent
  - [x] 10.1 Remove `update_ui` tool function and UI accumulator from `orchestrator-agent/src/orchestrator_agent/agent.py`
    - Delete the `update_ui` tool function
    - Delete `_ui_payloads` list, `_reset_ui_accumulator`, `_get_ui_payloads`, `_append_ui_payload`
    - Remove `update_ui` from `PYTHON_TOOLS` list
    - _Requirements: 3.1, 3.2_

  - [x] 10.2 Remove UI accumulator references from `orchestrator-agent/src/orchestrator_agent/agentcore_server.py`
    - Remove imports of `_reset_ui_accumulator`, `_get_ui_payloads` from agent module
    - Remove calls to these functions in `invoke()`
    - Remove the UI accumulator merge loop
    - _Requirements: 3.4_

  - [ ]* 10.3 Write unit tests verifying removal
    - Assert `update_ui` not in PYTHON_TOOLS list (Req 3.1)
    - Assert `_ui_payloads`, `_reset_ui_accumulator`, `_get_ui_payloads`, `_append_ui_payload` do not exist as module attributes (Req 3.2)
    - Assert agentcore_server does not call old accumulator functions (Req 3.4)
    - Test in `orchestrator-agent/tests/test_agent.py`
    - _Requirements: 3.1, 3.2, 3.4_

- [x] 11. Simplify orchestrator system prompt
  - [x] 11.1 Update `orchestrator-agent/src/orchestrator_agent/prompts/system_prompt.py`
    - Remove "CRITICAL: Structured UI Updates" section (all update_ui instructions)
    - Remove "CRITICAL: Capacity Impact Updates" section
    - Remove "CRITICAL: Transfer Orders on Funnel Completion" section
    - Add "Structured Data Handling" section explaining UI data is handled automatically by the server
    - Add instruction that Round 1 sub-agent invocations are handled automatically in parallel
    - Retain all workflow phase instructions, sub-agent coordination, Planner interaction, error handling, audit instructions
    - _Requirements: 3.3, 3.5, 11.1, 11.2, 11.3, 11.4, 11.5, 13.5_

  - [ ]* 11.2 Write unit tests for system prompt content
    - Assert removed sections are absent from prompt output
    - Assert retained sections (workflow phases, error handling, audit) are present
    - Assert new "Structured Data Handling" section is present
    - Assert Round 1 parallel instruction is present
    - Test in `orchestrator-agent/tests/test_system_prompt.py`
    - _Requirements: 3.3, 3.5, 11.1, 11.2, 11.3, 11.4, 11.5, 13.5_

- [x] 12. Simplify streaming proxy
  - [x] 12.1 Update `infrastructure/streaming-proxy/index.mjs`
    - Remove base64 trailer extraction (`<!--UI_B64:...:UI_B64-->` regex, Buffer.from/atob decoding)
    - Remove legacy trailer extraction (`<!--UI_DATA:...:UI_DATA-->` regex and JSON.parse)
    - Keep JSON envelope parsing: extract `result`, `ui`, `session_id`
    - Keep ALLOWED_UI_KEYS whitelist validation on `ui` field
    - When `ui` is missing from AgentCore response, default to empty object `{}`
    - Forward `{result, ui, session_id}` to browser
    - _Requirements: 4.2, 4.3, 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 12.2 Write property test for streaming proxy ui pass-through
    - **Property 12: Streaming proxy ui pass-through**
    - Generate random AgentCore response objects with various ui keys, verify only ALLOWED_UI_KEYS are forwarded with values unchanged
    - Test in `infrastructure/streaming-proxy/tests/proxy.test.ts` (vitest + fast-check)
    - **Validates: Requirements 4.3, 12.1, 12.2**

  - [ ]* 12.3 Write unit tests for proxy trailer removal verification
    - Assert no regex patterns for `<!--UI_B64:` or `<!--UI_DATA:` exist in index.mjs
    - Assert missing `ui` field returns empty object
    - _Requirements: 12.3, 12.4, 12.5_

- [x] 13. Simplify frontend streaming module
  - [x] 13.1 Update `frontend-spa/src/lib/streaming.ts` `handleCompleteResponse` function
    - Remove base64 trailer extraction (`<!--UI_B64:...:UI_B64-->` regex and `atob` decoding)
    - Remove legacy trailer extraction (`<!--UI_DATA:...:UI_DATA-->` regex and JSON.parse)
    - Keep JSON envelope parsing: extract `result` as display text, `ui` as structured data
    - When `ui` is non-empty, attach as `uiData` on message and pass to `parseResponse`
    - When `ui` is empty or missing, pass null to `parseResponse`
    - _Requirements: 4.4, 4.5, 9.1, 9.2, 9.3, 9.4_

  - [ ]* 13.2 Write property test for frontend envelope extraction
    - **Property 14: Frontend envelope extraction**
    - Generate random JSON envelopes with non-empty `ui` objects, verify `uiData` is attached to message and passed to `parseResponse`
    - Test in `frontend-spa/tests/streaming.test.ts` (vitest + fast-check)
    - **Validates: Requirements 9.1, 9.3**

  - [ ]* 13.3 Write unit tests for frontend trailer removal verification
    - Assert no regex patterns for `<!--UI_B64:` or `<!--UI_DATA:` exist in streaming.ts
    - Assert empty/missing `ui` results in null passed to `parseResponse`
    - _Requirements: 4.4, 9.2, 9.4_

- [x] 14. Checkpoint — Proxy and frontend simplification complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Verify schema preservation and round-trip property
  - [ ]* 15.1 Write property test for UiPayload JSON round-trip
    - **Property 15: UiPayload JSON round-trip**
    - Generate random `UiPayload` Pydantic instances via Hypothesis, serialize via `model_dump_json()`, deserialize via `UiPayload.model_validate_json()`, assert equivalence
    - Test in `orchestrator-agent/tests/test_schemas.py`
    - **Validates: Requirements 10.4**

  - [ ]* 15.2 Write unit tests for UiPayload schema field preservation
    - Assert all existing fields present on `UiPayload` Pydantic model (Req 10.1)
    - Assert frontend `UiPayload` TypeScript interface retains matching fields (Req 10.2)
    - Assert `parseResponse` mapping logic unchanged (Req 10.3)
    - _Requirements: 10.1, 10.2, 10.3_

- [ ] 16. Final checkpoint — Full pipeline integration
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints at tasks 4, 9, 14, and 16 ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–17)
- Unit tests validate specific examples, edge cases, and code structure checks
- Python tests use `pytest` + `hypothesis` (min 100 examples per property)
- TypeScript tests use `vitest` + `fast-check` (min 100 runs per property)
