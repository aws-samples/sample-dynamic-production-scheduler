# NFR Requirements — Unit 5: Capacity & Optimization Agent

## Performance Requirements

### PERF-CO-01: End-to-End Capacity Analysis Time
- Full 5-dimension capacity analysis must complete within 60 seconds
- Includes: 6 MCP tool calls, LLM reasoning, surplus calculations, bottleneck identification, shared context write
- MCP tool calls via HTTP/SSE to AgentCore Gateway add ~100-300ms per call

### PERF-CO-02: MCP Tool Call Latency
- Individual MCP tool calls must return within 2 seconds
- 6 primary data-fetch calls: get_machine_capacity (x2), get_manpower, get_materials, get_orders, get_customers
- Calls should be parallelized where possible to reduce total I/O time

### PERF-CO-03: LLM Inference Budget
- Claude 4.5 Haiku on Bedrock — optimized for speed
- LLM reasoning (system prompt + tool orchestration + explanation generation) should consume < 25 seconds of the 60s budget
- Remaining budget allocated to MCP I/O, calculations, and shared context writes

### PERF-CO-04: Delay Decision Response Time
- Single delay approval/rejection + recalculation must complete within 10 seconds
- Recalculation is pure arithmetic (no MCP data fetch needed, reuse cached snapshot)
- Includes: surplus update, bottleneck recalculation, LLM explanation, audit write

### PERF-CO-05: Constraint Recalculation Time
- Constraint application + before/after comparison must complete within 10 seconds
- Includes: constraint parsing, surplus recalculation, bottleneck update, LLM explanation
- No MCP data fetch needed — operates on cached capacity snapshot

---

## Reliability Requirements

### REL-CO-01: MCP Tool Failure Handling
- get_machine_capacity fails: agent halts, reports error (capacity is core)
- get_orders fails: agent halts, reports error (order load is core)
- get_manpower fails: proceed with manpower marked "unavailable" (per BR-CO-15)
- get_materials fails: proceed with materials marked "unavailable" (per BR-CO-15)
- get_customers fails: proceed without penalty_clause data (default false)
- write_audit_entry fails: log warning, continue workflow

### REL-CO-02: Agent Restart Behavior
- Agent is stateless — no in-memory state to recover
- If agent crashes mid-analysis, Orchestrator can re-invoke from scratch
- Shared context written only after successful analysis (atomic write)
- Delay decisions are persisted individually (each decision updates shared context)

### REL-CO-03: LLM Retry Strategy
- Bedrock throttling: retry with exponential backoff (1s, 2s, 4s, max 3 attempts)
- Bedrock model errors: fail immediately, report to Orchestrator
- Bedrock timeout: fail after 30 seconds, report to Orchestrator

### REL-CO-04: Idempotency
- Capacity analysis with same input produces same output (deterministic calculations)
- LLM temperature set to 0 for deterministic tool orchestration
- Delay decisions are idempotent (approving same delay twice = same result)

---

## Observability Requirements

### OBS-CO-01: Structured Logging
- Python `logging` module with JSON formatter (consistent with Units 1, 3, and 4)
- Every MCP tool call logged: tool name, parameters, duration, success/failure
- Capacity analysis results logged: surplus summary, bottleneck machine, utilization percentages
- Delay decisions logged: order_id, action (approved/rejected), freed capacity
- Constraint events logged: constraint_text, before/after surplus delta

### OBS-CO-02: Log Fields
Every log entry includes:
- `timestamp` (ISO 8601)
- `level` (ERROR, WARNING, INFO)
- `agent_name` ("capacity_optimization_agent")
- `session_id` (workflow session correlation)
- `duration_ms` (for timed operations)
- `message` (human-readable)

### OBS-CO-03: Log Destination
- stdout (captured by AgentCore runtime logging)
- CloudWatch Log Group: `/disruptionai/capacity-optimization-agent`
- Log retention: 90 days minimum (SECURITY-14 compliance)

### OBS-CO-04: Audit Trail Integration
- All capacity analysis, delay decisions, and constraint events written to Audit MCP (per BR-CO-16)
- Audit entries are the primary decision record; agent logs are supplementary

---

## Security Requirements (SECURITY Extension)

### SEC-CO-01: Input Validation (SECURITY-05)
- Agent validates all inputs from Orchestrator (order_id format, constraint text length)
- MCP tool responses validated via Pydantic schemas before processing
- No raw LLM output used directly — all tool calls go through Strands SDK
- Constraint text sanitized (max 500 chars, no injection patterns)

### SEC-CO-02: No Hardcoded Credentials (SECURITY-12)
- Bedrock credentials via IAM role (AgentCore managed runtime)
- MCP Gateway endpoint URL configurable via environment variable
- No API keys or secrets in source code

### SEC-CO-03: Least Privilege (SECURITY-06)
- Agent IAM role scoped to:
  - `bedrock:InvokeModel` on Claude 4.5 Haiku model ARN only
  - MCP tool access controlled by AgentCore Gateway authorization
- No direct DynamoDB access — all data access through MCP tools

### SEC-CO-04: Error Sanitization (SECURITY-09)
- Agent error messages to Orchestrator are generic — no stack traces or internal details
- Full error context logged server-side only
- LLM responses sanitized before presenting to Planner (no system prompt leakage)

### SEC-CO-05: Fail Closed (SECURITY-15)
- On unhandled exception: agent returns error to Orchestrator, does not proceed
- Global exception handler wraps agent entry point
- No partial results returned on failure (capacity analysis is all-or-nothing)
- Delay decisions already persisted are NOT rolled back on subsequent failure

---

## Scalability Requirements

### SCALE-CO-01: Order Volume
- MVP: ~50 active Ohio orders per analysis run
- Surplus calculation is O(n) — linear in order count
- Delay candidate filtering is O(n) with sort O(n log n)
- No pagination needed at MVP scale
- For future: algorithm scales to 500+ orders without architectural change

### SCALE-CO-02: AgentCore Hosting
- Agent registered in Bedrock AgentCore managed runtime
- AgentCore handles scaling, health checks, and lifecycle
- Single-user MVP — no concurrent capacity analysis runs
