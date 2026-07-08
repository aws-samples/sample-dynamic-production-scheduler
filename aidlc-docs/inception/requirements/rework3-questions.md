# Rework Cycle 3 — Requirements Clarification Questions

Based on live test analysis and CloudWatch log investigation, I've identified the root causes of the sub-agent failures. Please answer the following questions to guide the fix implementation.

## Root Cause Summary (for context)

**Finding 1 — ConcurrencyException**: The orchestrator invokes impact assessment and capacity optimization agents simultaneously (Round 1). When the first invocation is still running and the orchestrator's retry fires, the Strands Agent raises `ConcurrencyException: Agent is already processing a request. Concurrent invocations are not supported.`

**Finding 2 — MaxTokensReachedException**: All 3 sub-agents use `max_tokens=4096`. After fetching ERP data (20 orders, customers, equipment, materials, manpower) and attempting Python tool calls with large JSON payloads, the LLM exhausts its output token budget mid-tool-call. The impact assessment agent failed after 3 attempts to format `score_orders_tool` input correctly. The constraint matching agent failed after evaluating ~5 of 20 orders through the funnel.

**Finding 3 — Tool input format confusion**: Sub-agent LLMs struggle to serialize large ERP datasets into the correct JSON string format for Python tools (e.g., `score_orders_tool` expects `orders_json` as a JSON string, but the LLM tried 3 different formats before running out of tokens).

---

## Question 1: Max Tokens Fix
The sub-agents currently use `max_tokens=4096`. Given the large ERP payloads (20 orders with details), what max_tokens value should we set for sub-agents?

A) 8192 (2x current — moderate increase, matches orchestrator)
B) 16384 (4x current — generous headroom for large datasets)
C) Leave at 4096 but reduce payload sizes by having agents request only needed fields
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2: Concurrency Handling
The orchestrator currently invokes impact assessment and capacity optimization agents in parallel during Round 1, causing ConcurrencyException on retry. How should we handle this?

A) Make Round 1 sub-agent calls sequential (invoke impact assessment first, then capacity optimization)
B) Keep parallel but create new agent instances per invocation (avoid reusing the same Strands Agent object)
C) Keep parallel but add proper concurrency guards (mutex/lock per agent instance)
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3: Tool Input Simplification
The LLM wastes tokens trying to format large JSON payloads for Python tools. Should we simplify the tool interfaces?

A) Yes — refactor Python tools to accept pre-parsed objects instead of JSON strings (agent passes structured data, tool handles parsing internally)
B) Yes — add a data-preparation tool that the agent calls first to stage data, then scoring/funnel tools read from staged state (no large JSON passing)
C) No — just increase max_tokens; the LLM will eventually get the format right with more token budget
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 4: Plant-Agnostic Support
The system was designed for Florida disruption (Florida = disrupted, Ohio = receiving). The live test used "snowstorm in Ohio" (reversed roles). The orchestrator adapted, but sub-agent tool parameter names reference specific plants (e.g., `ohio_orders_json` in funnel tool). Should we make the system fully plant-agnostic?

A) Yes — rename all plant-specific parameters to generic names (e.g., `receiving_plant_orders_json`) and update prompts to be direction-agnostic
B) Partial — keep current parameter names but update system prompts to clarify that either plant can be disrupted or receiving
C) No — the current behavior is acceptable since the orchestrator already adapts
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5: Retry and Error Recovery
Currently the orchestrator has `retry_limit=1` for sub-agent calls. Given the ConcurrencyException issue, should we improve retry behavior?

A) Increase retry limit to 2-3 with exponential backoff (wait before retrying to let the first invocation finish)
B) Keep retry_limit=1 but add a delay between retries (e.g., 30 seconds)
C) Remove retries entirely — if a sub-agent fails, the orchestrator should immediately fall back to manual analysis
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6: Orchestrator Model
The orchestrator currently uses Claude Haiku (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) with `max_tokens=8192`. During the live test, the orchestrator successfully completed the full workflow (including manual fallback analysis) but it's a complex multi-phase workflow. Should we upgrade the orchestrator model?

A) Upgrade to Claude Sonnet for better reasoning on the complex multi-phase workflow
B) Keep Haiku but increase max_tokens to 16384 for more headroom
C) Keep current configuration — it worked fine during the live test
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 7: Security Extension
Should security extension rules continue to be enforced for this rework cycle?

A) Yes — enforce all SECURITY rules as blocking constraints
B) No — skip security rules for this bug-fix rework
C) Other (please describe after [Answer]: tag below)

[Answer]: A
