# Rework 6 — Clarification Questions

I detected a conflict between your answers to Q2 and Q6 that needs resolution before I can generate requirements.

## Conflict: UI Data Delivery Mechanism

**Q2 answer (C + custom)**: Remove `json_extractor.py` entirely. Instead of having the LLM "type out" JSON, define a **UI tool** that the orchestrator calls when it needs to update the frontend. This means the `ui` data comes from **tool call results**, not from parsing LLM text.

**Q6 answer (A)**: Update the system prompt to instruct the LLM to emit **`disruptionai_json` fenced blocks** inline in its text response. This means the `ui` data comes from **parsing the LLM's text output** for JSON blocks.

These are fundamentally different approaches:
- **Tool-call approach** (Q2): The orchestrator registers a `update_ui` tool. When the LLM decides the frontend needs data, it calls the tool with structured arguments. The tool result is captured and attached as the `ui` field. The LLM's text response is purely for chat display.
- **Inline JSON block approach** (Q6): The LLM writes `disruptionai_json` blocks inside its text response. Server-side code extracts these blocks, strips them from the display text, and attaches them as the `ui` field.

---

## Clarification Question 1
Which approach should be used for delivering structured UI data from the orchestrator to the frontend?

A) Tool-call approach — register a `update_ui` tool on the orchestrator. The LLM calls it with structured data (phase, orders, capacity, approvalRequest). The tool result becomes the `ui` field. No JSON parsing of LLM text needed.
B) Inline JSON block approach — the LLM emits `disruptionai_json` fenced blocks in its text. Server-side code extracts and validates them. Simpler to implement but relies on the LLM formatting JSON correctly.
C) Hybrid — use tool calls for critical structured data (orders, approval requests) and inline JSON for lightweight metadata (phase, agent status)
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

