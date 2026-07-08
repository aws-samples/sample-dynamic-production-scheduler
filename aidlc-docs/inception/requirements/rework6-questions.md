# Rework 6 — Structured JSON Response Pipeline: Clarification Questions

The current disruption workflow pipeline has a data loss problem: the orchestrator's `agentcore_server.py` returns a JSON envelope `{"result": ..., "ui": {...}, "session_id": ...}` but the Lambda streaming proxy pipes the AgentCore SSE stream raw — the `ui` field is lost in transit. The frontend compensates with ~300 lines of regex extraction in `streaming.ts` and `responseParser.ts`, which is fragile and breaks when the LLM changes wording.

You want to fix this end-to-end so the `ui` field survives from orchestrator → AgentCore → Lambda proxy → browser, and all disruption components render from `msg.uiData` instead of regex-parsed text.

Please answer each question by filling in the letter choice after the `[Answer]:` tag.

---

## Question 1
The Lambda streaming proxy currently does `pipeline(runtimeResponse.response, httpStream)` — a raw pipe. How should it handle the AgentCore response to preserve the `ui` field?

A) Buffer the entire AgentCore response, parse the JSON envelope, and forward the complete envelope as a single JSON response (no SSE streaming)
B) Buffer the entire response, parse the envelope, then re-emit as SSE with the `ui` field included in the final `data:` event
C) Parse each SSE chunk from AgentCore, detect the final chunk containing the JSON envelope, and inject the `ui` field into the forwarded stream
D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 2
Should the orchestrator's `json_extractor.py` (server-side regex extraction) be kept, replaced, or removed?

A) Keep it as-is — it provides a useful server-side extraction layer even with structured JSON
B) Replace it — have the orchestrator's system prompt instruct the LLM to emit structured `disruptionai_json` blocks, and `json_extractor.py` just validates/passes them through
C) Remove it entirely — the orchestrator should return raw text and the `ui` field should be built from explicit tool call results (not LLM text parsing)
D) Other (please describe after [Answer]: tag below)

[Answer]: C, and Instead of having the LLM "type out" JSON blocks in its response for you to extract, you should define a specific UI tool that the orchestrator calls when it needs to update the frontend.

---

## Question 3
For the frontend, how aggressively should the regex-based text parsing be removed?

A) Remove all regex parsing — if `msg.uiData` is missing, show the raw text as markdown (no extraction)
B) Keep regex parsing as a degraded fallback — try `msg.uiData` first, fall back to regex if missing
C) Remove regex from disruption components only — keep it for the general chat view
D) Other (please describe after [Answer]: tag below)

[Answer]: A 
---

## Question 4
The `ui` field schema is currently ad-hoc (whatever `json_extractor.py` produces). Should a formal schema be defined?

A) Yes — define a TypeScript interface and a matching Python dataclass/Pydantic model for the `ui` payload, validated on both sides
B) Partial — define a TypeScript interface on the frontend for type safety, but keep the Python side flexible
C) No — keep it loosely typed; the frontend components already know what fields to expect
D) Other (please describe after [Answer]: tag below)

[Answer]: A) Yes — define a TypeScript interface and a matching Python dataclass/Pydantic model for the ui payload, validated on both sides

---

## Question 5
The current `handleCompleteResponse()` in `streaming.ts` has ~80 lines of JSON unwrapping logic (double-encoded strings, nested envelopes, Lambda response wrappers). After fixing the proxy, how much of this should remain?

A) Strip it down to minimal: parse JSON → extract `result` + `ui` → done. Remove all the fallback/unwrapping paths.
B) Keep the fallback paths but simplify — the proxy fix should make them rarely hit, but they're good defensive coding
C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 6
Should the orchestrator's system prompt be updated to explicitly produce structured JSON blocks (e.g., `disruptionai_json` fenced blocks) for each phase, or should the `ui` field continue to be extracted post-hoc from natural language?

A) Update the system prompt — instruct the LLM to emit `disruptionai_json` blocks with phase, orders, capacity, approvalRequest fields alongside its natural language explanation
B) Keep post-hoc extraction — the LLM writes natural language and `json_extractor.py` extracts structure server-side
C) Hybrid — update the prompt for critical data (orders, approval requests) but keep post-hoc extraction for phase detection and capacity
D) Other (please describe after [Answer]: tag below)

[Answer]: A) Update the system prompt — instruct the LLM to emit disruptionai_json blocks with phase, orders, capacity, approvalRequest fields alongside its natural language explanation


---

## Question 7
Security Baseline extension is enabled. The Lambda proxy change introduces a new response format. Should the response be validated/sanitized before forwarding to the browser?

A) Yes — validate that the `ui` field conforms to expected schema before forwarding; strip unexpected fields
B) Minimal — ensure the `ui` field is valid JSON and doesn't contain script injection, but don't validate schema
C) No additional validation needed — the data originates from our own orchestrator, not user input
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

