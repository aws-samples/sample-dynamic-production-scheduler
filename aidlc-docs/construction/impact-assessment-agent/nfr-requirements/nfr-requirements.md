# NFR Requirements — Unit 4: Impact Assessment Agent

## Performance Requirements

### PERF-IA-01: End-to-End Classification Time
- Full priority classification of 20 Florida orders must complete within 30 seconds
- Includes: MCP tool calls (get_orders, get_customers), LLM reasoning, scoring, shared context write
- MCP tool calls via HTTP/SSE to AgentCore Gateway add network latency (~100-300ms per call)

### PERF-IA-02: MCP Tool Call Latency
- Individual MCP tool calls (HTTP/SSE to AgentCore Gateway) must return within 2 seconds
- get_orders and get_customers are the two primary data-fetch calls
- update_order_priority calls (one per order) should be batched or parallelized where possible

### PERF-IA-03: LLM Inference Budget
- Agent uses Claude 4.5 Haiku on Bedrock — optimized for speed
- LLM reasoning (system prompt + tool orchestration) should consume < 15 seconds of the 30s budget
- Remaining budget allocated to MCP I/O and shared context writes

### PERF-IA-04: Reclassification Response Time
- Single order reclassification (override + re-evaluate non-pinned) must complete within 10 seconds
- Re-evaluation is a subset of full classification (no data fetch needed, reuse cached orders)

---

## Reliability Requirements

### REL-IA-01: MCP Tool Failure Handling
- If get_orders fails: agent halts and reports error to Orchestrator (per BR-IA-12)
- If get_customers fails: agent proceeds with default tier scores (per BR-IA-13)
- If write_audit_entry fails: agent logs warning, continues workflow (per BR-IA-13)
- If update_order_priority fails: retry once, then report partial failure to Orchestrator

### REL-IA-02: Agent Restart Behavior
- Agent is stateless — no in-memory state to recover
- If agent crashes mid-classification, Orchestrator can re-invoke from scratch
- Shared context is only written after successful classification (atomic write)
- Partial priority updates (some orders updated, some not) are acceptable — re-run will overwrite

### REL-IA-03: LLM Retry Strategy
- Bedrock throttling (ThrottlingException): retry with exponential backoff (1s, 2s, 4s, max 3 attempts)
- Bedrock model errors (ModelErrorException): fail immediately, report to Orchestrator
- Bedrock timeout: fail after 20 seconds, report to Orchestrator

### REL-IA-04: Idempotency
- Running classification twice with same input produces same output (deterministic scoring)
- LLM temperature set to 0 for deterministic tool orchestration
- Priority updates via update_order_priority are idempotent (setting P1 twice = same result)

---

## Observability Requirements

### OBS-IA-01: Structured Logging
- Python `logging` module with JSON formatter (consistent with Units 1 and 3)
- Every MCP tool call logged: tool name, parameters, duration, success/failure
- Classification results logged: order count, P1/P2/P3 distribution, weights used
- Reclassification events logged: order_id, old_priority, new_priority

### OBS-IA-02: Log Fields
Every log entry includes:
- `timestamp` (ISO 8601)
- `level` (ERROR, WARNING, INFO)
- `agent_name` ("impact_assessment_agent")
- `session_id` (workflow session correlation)
- `duration_ms` (for timed operations)
- `message` (human-readable)

### OBS-IA-03: Log Destination
- stdout (captured by AgentCore runtime logging)
- CloudWatch Log Group: `/disruptionai/impact-assessment-agent`
- Log retention: 90 days minimum (SECURITY-14 compliance)

### OBS-IA-04: Audit Trail Integration
- All classification and reclassification decisions written to Audit MCP (per BR-IA-14)
- Audit entries are the primary decision record; agent logs are supplementary

---

## Security Requirements (SECURITY Extension)

### SEC-IA-01: Input Validation (SECURITY-05)
- Agent validates all inputs from Orchestrator (order_id format, priority enum)
- MCP tool responses validated via Pydantic schemas before processing
- No raw LLM output used directly — all tool calls go through Strands SDK

### SEC-IA-02: No Hardcoded Credentials (SECURITY-12)
- Bedrock credentials via IAM role (AgentCore managed runtime)
- MCP Gateway endpoint URL configurable via environment variable
- No API keys or secrets in source code

### SEC-IA-03: Least Privilege (SECURITY-06)
- Agent IAM role scoped to:
  - `bedrock:InvokeModel` on Claude 4.5 Haiku model ARN only
  - MCP tool access controlled by AgentCore Gateway authorization
- No direct DynamoDB access — all data access through MCP tools

### SEC-IA-04: Error Sanitization (SECURITY-09)
- Agent error messages to Orchestrator are generic — no stack traces or internal details
- Full error context logged server-side only
- LLM responses sanitized before presenting to Planner (no system prompt leakage)

### SEC-IA-05: Fail Closed (SECURITY-15)
- On unhandled exception: agent returns error to Orchestrator, does not proceed
- Global exception handler wraps agent entry point
- No partial results returned on failure (classification is all-or-nothing)

---

## Scalability Requirements

### SCALE-IA-01: Order Volume
- MVP: 20 Florida orders per classification run
- Scoring algorithm is O(n) — linear in order count
- No pagination needed at MVP scale
- For future: algorithm scales to 200+ orders without architectural change

### SCALE-IA-02: AgentCore Hosting
- Agent registered in Bedrock AgentCore managed runtime
- AgentCore handles scaling, health checks, and lifecycle
- Single-user MVP — no concurrent classification runs
