# Requirements Document

## Introduction

This feature reworks the orchestrator agent's response pipeline to eliminate LLM-driven JSON formatting and replace it with deterministic structured outputs. Currently, the orchestrator relies on the LLM calling an `update_ui` tool to produce structured JSON for the frontend, achieving only ~82% accuracy. The `update_ui` tool output is embedded as base64 trailers in response text, parsed through multiple layers (AgentCore → streaming proxy → frontend), and frequently gets lost or malformed. A regex-based `_extract_ui_fallback` attempts to recover structured data from free-form LLM text when `update_ui` is not called.

The proposed architecture has sub-agents return validated Pydantic objects via Strands `structured_output_model`, the orchestrator build the `ui` dict deterministically in Python from those structured outputs, and the entire trailer/fallback extraction system removed from the streaming proxy and frontend.

## Glossary

- **Orchestrator_Agent**: The coordinating Strands Agent that routes tasks to sub-agents, manages workflow phases, and returns responses to the frontend via AgentCore Runtime.
- **Impact_Assessment_Agent**: Sub-agent that scores and prioritizes production orders by urgency, customer tier, value, and machine complexity.
- **Capacity_Optimization_Agent**: Sub-agent that analyzes receiving plant capacity across 5 dimensions and manages delay candidates.
- **Constraint_Matching_Agent**: Sub-agent that runs the 4-layer constraint funnel for order rerouting decisions.
- **Structured_Output_Model**: The Strands Agents SDK `structured_output_model` parameter that constrains an agent's final response to a validated Pydantic model.
- **UI_Payload**: The validated JSON object sent to the frontend containing phase, orders, capacity, approvalRequest, capacityImpact, and transferOrders fields.
- **Streaming_Proxy**: The Lambda function (index.mjs) that sits between the browser and AgentCore Runtime, forwarding requests and responses.
- **AgentCore_Server**: The per-agent `agentcore_server.py` entry point that handles AgentCore Runtime invocations and returns response dicts.
- **Trailer_System**: The current mechanism that embeds UI data as `<!--UI_B64:...:UI_B64-->` comments in agent response text for extraction downstream.
- **Fallback_Extractor**: The `_extract_ui_fallback` function in the orchestrator's agentcore_server.py that uses regex to parse structured data from free-form LLM text.
- **CapacityState**: The in-memory cache in the Capacity_Optimization_Agent that tracks cumulative capacity changes across delay and constraint decisions.
- **Round1_Result**: The combined output of Impact_Assessment_Agent (scored orders, priorities) and Capacity_Optimization_Agent (capacity snapshot) during intelligence gathering.
- **Delay_Decision_Result**: The output of Capacity_Optimization_Agent's `process_delay_decision` tool containing surplus_after and bottleneck_after data.
- **Funnel_Result**: The output of Constraint_Matching_Agent's `evaluate_funnel_tool` containing per-layer pass/fail results and recommendation.

## Requirements

### Requirement 1: Sub-Agent Structured Output

**User Story:** As a system operator, I want sub-agents to return validated Pydantic objects instead of free-form text, so that the orchestrator receives machine-parseable data with guaranteed schema compliance.

#### Acceptance Criteria

1. WHEN the Impact_Assessment_Agent completes an invocation, THE Impact_Assessment_Agent SHALL return a response conforming to a Pydantic model containing scored orders, priority summary, and total value fields.
2. WHEN the Capacity_Optimization_Agent completes an invocation, THE Capacity_Optimization_Agent SHALL return a response conforming to a Pydantic model containing capacity snapshot, delay candidates, surplus summary, and bottleneck fields.
3. WHEN the Constraint_Matching_Agent completes an invocation, THE Constraint_Matching_Agent SHALL return a response conforming to a Pydantic model containing funnel results, recommendation, and per-layer pass/fail details.
4. THE Impact_Assessment_Agent SHALL use the Strands `structured_output_model` parameter to enforce the response schema at agent creation time.
5. THE Capacity_Optimization_Agent SHALL use the Strands `structured_output_model` parameter to enforce the response schema at agent creation time.
6. THE Constraint_Matching_Agent SHALL use the Strands `structured_output_model` parameter to enforce the response schema at agent creation time.
7. WHEN a sub-agent returns a structured response, THE sub-agent's AgentCore_Server SHALL serialize the Pydantic model to a JSON dict and include it in the response payload under a `structured_output` key.
8. IF a sub-agent's structured output fails Pydantic validation, THEN THE sub-agent's AgentCore_Server SHALL return an error response with a descriptive validation error message.

### Requirement 2: Orchestrator Deterministic UI Assembly

**User Story:** As a frontend developer, I want the orchestrator to build UI payloads deterministically in Python code rather than relying on LLM tool calls, so that the frontend receives consistent, complete structured data on every response.

#### Acceptance Criteria

1. WHEN the Orchestrator_Agent's AgentCore_Server receives a successful sub-agent response containing a `structured_output` key, THE AgentCore_Server SHALL extract the structured data and use it to build the UI_Payload.
2. THE Orchestrator_Agent's AgentCore_Server SHALL build the `ui` dict by mapping sub-agent structured output fields to UI_Payload fields using deterministic Python code with no LLM involvement.
3. WHEN the workflow is in the round1_in_progress phase and both sub-agents complete, THE AgentCore_Server SHALL assemble a `round1_complete` UI_Payload containing orders, capacity, priorities, totalOrders, totalValue, and bottleneck fields from the combined sub-agent outputs.
4. WHEN the workflow is in the round2_delays phase and a delay decision completes, THE AgentCore_Server SHALL assemble a `delay_optimization` UI_Payload containing the approvalRequest for the next candidate and capacityImpact from the Capacity_Optimization_Agent's Delay_Decision_Result.
5. WHEN the workflow is in the round2_funnel phase and a funnel evaluation completes, THE AgentCore_Server SHALL assemble a `constraint_funnel` UI_Payload containing the approvalRequest with funnelResults and capacityImpact.
6. WHEN the workflow reaches the summary phase, THE AgentCore_Server SHALL assemble a `summary` UI_Payload containing complete=true and transferOrders from accumulated funnel approvals.
7. THE Orchestrator_Agent's AgentCore_Server SHALL include the assembled `ui` dict as a top-level key in the response JSON envelope alongside `result` and `session_id`.

### Requirement 3: Remove update_ui Tool and UI Accumulator

**User Story:** As a system maintainer, I want the `update_ui` tool, UI accumulator, and all related prompt instructions removed from the orchestrator, so that the codebase has a single deterministic path for UI data and no dead code.

#### Acceptance Criteria

1. THE Orchestrator_Agent SHALL NOT include the `update_ui` function in its PYTHON_TOOLS list.
2. THE Orchestrator_Agent SHALL NOT contain the `_ui_payloads` module-level list, `_reset_ui_accumulator`, `_get_ui_payloads`, or `_append_ui_payload` functions.
3. THE Orchestrator_Agent's system prompt SHALL NOT contain instructions for calling `update_ui`, including the "CRITICAL: Structured UI Updates", "CRITICAL: Capacity Impact Updates", and "CRITICAL: Transfer Orders on Funnel Completion" sections.
4. THE Orchestrator_Agent's AgentCore_Server SHALL NOT call `_reset_ui_accumulator` or `_get_ui_payloads`.
5. THE Orchestrator_Agent's system prompt SHALL retain all workflow phase instructions, sub-agent coordination rules, and Planner interaction rules unrelated to `update_ui`.

### Requirement 4: Remove Trailer System

**User Story:** As a system maintainer, I want the base64 trailer embedding, trailer extraction in the streaming proxy, and trailer extraction in the frontend removed, so that the response pipeline uses a single clean JSON envelope with no embedded comment markers.

#### Acceptance Criteria

1. THE Orchestrator_Agent's AgentCore_Server SHALL NOT embed `<!--UI_B64:...:UI_B64-->` or `<!--UI_DATA:...:UI_DATA-->` comment markers in the result text.
2. THE Streaming_Proxy SHALL NOT contain regex patterns for matching or extracting `<!--UI_B64:...:UI_B64-->` or `<!--UI_DATA:...:UI_DATA-->` trailers.
3. THE Streaming_Proxy SHALL forward the `ui` field from the AgentCore response JSON envelope directly to the browser response without trailer extraction logic.
4. THE frontend streaming module SHALL NOT contain regex patterns for matching or extracting `<!--UI_B64:...:UI_B64-->` or `<!--UI_DATA:...:UI_DATA-->` trailers.
5. THE frontend streaming module SHALL read the `ui` field from the JSON envelope as the sole source of structured UI data.
6. THE Orchestrator_Agent's AgentCore_Server SHALL NOT perform ASCII-only encoding of result text (the `encode("ascii", errors="ignore")` sanitization step).

### Requirement 5: Remove Fallback Extractor

**User Story:** As a system maintainer, I want the regex-based `_extract_ui_fallback` function removed from the orchestrator's agentcore_server.py, so that there is no unreliable text-parsing path for structured data.

#### Acceptance Criteria

1. THE Orchestrator_Agent's AgentCore_Server SHALL NOT contain the `_extract_ui_fallback` function.
2. THE Orchestrator_Agent's AgentCore_Server SHALL NOT call `_extract_ui_fallback` as a fallback when the `ui` dict is empty.
3. WHEN the orchestrator LLM does not produce structured data for a response, THE AgentCore_Server SHALL return an empty `ui` dict rather than attempting text extraction.

### Requirement 6: Capacity Impact from Deterministic Computation

**User Story:** As a frontend developer, I want capacityImpact data to come from the Capacity_Optimization_Agent's deterministic Python computations rather than LLM-formatted JSON, so that capacity utilization percentages are accurate and consistent.

#### Acceptance Criteria

1. WHEN the Capacity_Optimization_Agent's `process_delay_decision` tool completes, THE tool SHALL include a `capacityImpact` field in its return value containing current and projected utilization for both sender and receiver plants.
2. WHEN the Capacity_Optimization_Agent's `apply_constraint_tool` completes, THE tool SHALL include a `capacityImpact` field in its return value containing current and projected utilization for both sender and receiver plants.
3. THE capacityImpact field SHALL contain senderPlant and receiverPlant objects, each with name, rollingMill (current, projected), finishingLine (current, projected), and overall (current, projected) fields.
4. THE capacityImpact utilization values SHALL be computed from the CapacityState cached snapshot using deterministic arithmetic, not LLM-generated values.
5. WHEN the Orchestrator_Agent's AgentCore_Server builds the UI_Payload for delay_optimization or constraint_funnel phases, THE AgentCore_Server SHALL use the capacityImpact from the sub-agent's tool return value.

### Requirement 7: Sub-Agent AgentCore Server Structured Response

**User Story:** As a system integrator, I want each sub-agent's agentcore_server.py to return the Pydantic structured output as a JSON dict in the response, so that the orchestrator can parse it without text extraction.

#### Acceptance Criteria

1. WHEN the Impact_Assessment_Agent's AgentCore_Server receives a successful agent result, THE AgentCore_Server SHALL extract the structured output from the agent result and include it as a `structured_output` key in the response dict.
2. WHEN the Capacity_Optimization_Agent's AgentCore_Server receives a successful agent result, THE AgentCore_Server SHALL extract the structured output from the agent result and include it as a `structured_output` key in the response dict.
3. WHEN the Constraint_Matching_Agent's AgentCore_Server receives a successful agent result, THE AgentCore_Server SHALL extract the structured output from the agent result and include it as a `structured_output` key in the response dict.
4. IF a sub-agent invocation fails, THEN THE sub-agent's AgentCore_Server SHALL return an error response without a `structured_output` key.

### Requirement 8: Orchestrator Sub-Agent Invocation Parsing

**User Story:** As a system integrator, I want the orchestrator's sub-agent invocation helper to parse structured output from sub-agent responses, so that the deterministic UI assembly has typed data to work with.

#### Acceptance Criteria

1. WHEN the Orchestrator_Agent's `_invoke_sub_agent` helper receives a response from AgentCore Runtime, THE helper SHALL parse the response body as JSON and extract the `structured_output` field if present.
2. WHEN a `structured_output` field is present in the sub-agent response, THE `_invoke_sub_agent` helper SHALL store the parsed structured data in a module-level or session-level accumulator accessible to the AgentCore_Server.
3. IF the sub-agent response does not contain a `structured_output` field, THEN THE `_invoke_sub_agent` helper SHALL continue to return the text output to the LLM as before.
4. THE `_invoke_sub_agent` helper SHALL continue to return the text summary to the orchestrator LLM for reasoning, in addition to storing the structured output.

### Requirement 9: Frontend Streaming Simplification

**User Story:** As a frontend developer, I want the streaming module to read structured UI data exclusively from the JSON envelope's `ui` field, so that the code is simpler and there is a single source of truth for UI data.

#### Acceptance Criteria

1. THE frontend streaming module's `handleCompleteResponse` function SHALL parse the JSON envelope and extract the `ui` field as the sole source of UI_Payload data.
2. THE frontend streaming module SHALL NOT contain fallback extraction logic for base64-encoded or legacy JSON-embedded UI data.
3. WHEN the JSON envelope contains a non-empty `ui` object, THE frontend streaming module SHALL attach it to the message as `uiData` and pass it to `parseResponse`.
4. WHEN the JSON envelope contains an empty or missing `ui` object, THE frontend streaming module SHALL pass null to `parseResponse`, resulting in plain text display.

### Requirement 10: UI Payload Schema Preservation

**User Story:** As a frontend developer, I want the UI_Payload schema (UiPayload Pydantic model and TypeScript UiPayload interface) to remain unchanged, so that the frontend components continue to work without modification.

#### Acceptance Criteria

1. THE Orchestrator_Agent's UiPayload Pydantic model in schemas.py SHALL retain all existing fields: phase, agents, orders, capacity, priorities, approvalRequest, totalOrders, totalValue, bottleneck, complete, capacityImpact, and transferOrders.
2. THE frontend UiPayload TypeScript interface SHALL retain all existing fields matching the Pydantic model.
3. THE frontend responseParser module SHALL continue to map UI_Payload fields to Zustand store actions using the same logic as the current implementation.
4. FOR ALL valid UI_Payload objects produced by the deterministic assembly, serializing to JSON and deserializing back SHALL produce an equivalent object (round-trip property).

### Requirement 11: Orchestrator System Prompt Simplification

**User Story:** As a system maintainer, I want the orchestrator's system prompt reduced by removing all `update_ui` instructions, capacityImpact formatting instructions, and transferOrders formatting instructions, so that the prompt is shorter, the LLM has fewer conflicting directives, and token usage is reduced.

#### Acceptance Criteria

1. THE Orchestrator_Agent's system prompt SHALL NOT contain the "CRITICAL: Structured UI Updates" section or any instructions directing the LLM to call `update_ui`.
2. THE Orchestrator_Agent's system prompt SHALL NOT contain the "CRITICAL: Capacity Impact Updates" section or any instructions directing the LLM to format capacityImpact JSON.
3. THE Orchestrator_Agent's system prompt SHALL NOT contain the "CRITICAL: Transfer Orders on Funnel Completion" section or any instructions directing the LLM to format transferOrders JSON.
4. THE Orchestrator_Agent's system prompt SHALL retain workflow phase instructions, sub-agent coordination rules, Planner interaction rules, error handling rules, and audit instructions.
5. THE Orchestrator_Agent's system prompt SHALL inform the LLM that structured UI data is handled automatically by the server and the LLM's role is to provide natural language responses for the chat display.

### Requirement 12: Streaming Proxy Simplification

**User Story:** As a system maintainer, I want the streaming proxy Lambda to forward the `ui` field from the AgentCore JSON envelope directly without any trailer extraction or sanitization logic, so that the proxy is a thin pass-through.

#### Acceptance Criteria

1. THE Streaming_Proxy SHALL parse the AgentCore response as JSON and extract the `result`, `ui`, and `session_id` fields.
2. THE Streaming_Proxy SHALL forward the `ui` field to the browser response as-is, applying only the existing ALLOWED_UI_KEYS whitelist validation.
3. THE Streaming_Proxy SHALL NOT contain base64 decoding logic for `<!--UI_B64:...:UI_B64-->` patterns.
4. THE Streaming_Proxy SHALL NOT contain JSON extraction logic for `<!--UI_DATA:...:UI_DATA-->` patterns.
5. WHEN the AgentCore response does not contain a `ui` field, THE Streaming_Proxy SHALL include an empty `ui` object in the browser response.


### Requirement 13: Deterministic Parallel Sub-Agent Invocation in Round 1

**User Story:** As a production planner, I want the Impact Assessment and Capacity Optimization sub-agents to always run in parallel during Round 1 intelligence gathering, so that the combined analysis completes in roughly half the time and parallelism is guaranteed rather than dependent on LLM behavior.

#### Acceptance Criteria

1. WHEN the Orchestrator_Agent enters the Round 1 intelligence gathering phase, THE Orchestrator_Agent SHALL invoke the Impact_Assessment_Agent and Capacity_Optimization_Agent in parallel using deterministic code (e.g., Python threading, concurrent.futures, or Strands Graph pattern), not by relying on the LLM to emit both tool calls in a single turn.
2. THE parallel invocation mechanism SHALL use the existing `_invoke_sub_agent` helper for each sub-agent call, preserving retry logic, error recording, and structured output extraction.
3. WHEN both Round 1 sub-agents complete successfully, THE Orchestrator_Agent's AgentCore_Server SHALL combine both structured outputs into a single `round1_complete` UI_Payload before returning the response.
4. IF one Round 1 sub-agent fails while the other succeeds, THE Orchestrator_Agent SHALL return partial results from the successful sub-agent and include an error indicator for the failed sub-agent in the UI_Payload.
5. THE Orchestrator_Agent's system prompt SHALL instruct the LLM that Round 1 sub-agent invocations are handled automatically in parallel and the LLM should wait for the combined results before generating its summary text.
