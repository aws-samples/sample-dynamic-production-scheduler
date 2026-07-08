# NFR Requirements — Unit 6: Constraint Matching Agent

## Performance Requirements

### PERF-CM-01: Per-Order Funnel Latency
- Each order's 4-layer constraint funnel evaluation must complete within 15 seconds
- Includes: 4 layer checks, LLM reasoning per layer, natural language explanation generation
- Budget breakdown:
  - Layer 1 (Equipment): < 1 second (simple lookup, no LLM needed)
  - Layer 2 (Material): < 2 seconds (arithmetic + procurement feasibility)
  - Layer 3 (Utilization): < 2 seconds (tiered surplus check + manpower)
  - Layer 4 (Cascade): < 3 seconds (multi-level simulation, timeout enforced)
  - LLM explanation generation: < 5 seconds (natural language per-layer reasoning)
  - Recommendation + presentation: < 2 seconds

### PERF-CM-02: MCP Tool Call Latency
- Individual MCP tool calls (HTTP/SSE to AgentCore Gateway) must return within 2 seconds
- Initialization calls: get_machine_capacity (x2), get_materials, get_orders, get_manpower, get_running_tracker
- Per-decision calls: update_running_tracker (~100-300ms per write)
- Initialization calls should be parallelized where possible

### PERF-CM-03: LLM Inference Budget
- Claude 4.5 Haiku on Bedrock — optimized for speed
- LLM reasoning per order should consume < 7 seconds of the 15s budget
- Remaining budget allocated to MCP I/O, calculations, and cascade simulation

### PERF-CM-04: Decision Processing Time
- Single approve/reject/skip + tracker update + audit write must complete within 5 seconds
- Approve: tracker deduction + DynamoDB write + audit write
- Skip: queue update + DynamoDB write + audit write
- Reject: mark non-transferable + DynamoDB write + audit write

### PERF-CM-05: Cascade Simulation Timeout
- Layer 4 multi-level cascade simulation has a 3-second hard timeout
- If simulation exceeds 3 seconds, return results computed so far
- Include warning: "Cascade simulation timed out at level {N} of {max_depth}. Results may be incomplete."
- Timeout applies to the cascade computation only, not the full Layer 4 evaluation

### PERF-CM-06: Tracker Persistence Strategy
- Write tracker to DynamoDB via update_running_tracker after EVERY planner decision
- Additionally, periodic checkpoint every 5 minutes during idle periods (planner thinking time)
- Checkpoint ensures tracker state survives agent restarts even if planner hasn't made a decision recently
- Each write is ~100-300ms — acceptable within the 5s decision processing budget

### PERF-CM-07: Revisit Re-evaluation Time
- When planner requests "Go back to Order #X", full funnel re-evaluation within 15 seconds
- Same budget as initial evaluation (PERF-CM-01)
- No additional MCP data fetch needed — reuse cached equipment/material/Ohio data

---

## Reliability Requirements

### REL-CM-01: MCP Tool Failure Handling
- get_machine_capacity fails: agent halts, reports error (equipment data is core for Layer 1)
- get_materials fails: Layer 2 defaults to "No Match" with warning (per BR-CM-13)
- get_orders(Ohio) fails: Layer 4 defaults to PASS with warning (per BR-CM-13)
- get_manpower fails: manpower check defaults to soft warning (per BR-CM-13)
- get_running_tracker fails: initialize fresh tracker from shared context snapshot
- update_running_tracker fails: log warning, continue with in-memory tracker
- write_audit_entry fails: log warning, continue workflow

### REL-CM-02: Agent Restart Behavior
- Agent loads tracker from DynamoDB on startup (session resumption)
- If tracker exists: skip already-processed orders, resume from next unprocessed
- If tracker missing: initialize from shared context snapshot, start from first order
- Periodic checkpoint (every 5 minutes) ensures minimal data loss on crash

### REL-CM-03: LLM Retry Strategy
- Bedrock throttling (ThrottlingException): retry with exponential backoff (1s, 2s, 4s, max 3 attempts)
- Bedrock model errors (ModelErrorException): fail immediately, report to Orchestrator
- Bedrock timeout: fail after 20 seconds per LLM call, report to Orchestrator

### REL-CM-04: Idempotency
- Funnel evaluation with same input and same tracker state produces same output
- LLM temperature set to 0 for deterministic tool orchestration
- Tracker updates are idempotent (approving same order twice = same deduction)
- DynamoDB writes use session_id scoping — no cross-session interference

### REL-CM-05: Session Isolation
- Multiple planners can run constraint matching simultaneously with independent trackers
- Each session has a unique session_id scoping its tracker in DynamoDB
- No shared mutable state between sessions
- Tracker key: `{session_id}` — ensures complete isolation

---

## Observability Requirements

### OBS-CM-01: Structured Logging
- Python `logging` module with JSON formatter (consistent with Units 1, 3, 4, and 5)
- Every MCP tool call logged: tool name, parameters, duration, success/failure
- Every funnel evaluation logged: order_id, layer results (pass/fail), recommendation
- Every planner decision logged: order_id, action, capacity consumed
- Cascade simulation logged: depth reached, orders impacted, timeout status

### OBS-CM-02: Log Fields
Every log entry includes:
- `timestamp` (ISO 8601)
- `level` (ERROR, WARNING, INFO)
- `agent_name` ("constraint_matching_agent")
- `session_id` (workflow session correlation)
- `order_id` (when processing a specific order)
- `duration_ms` (for timed operations)
- `message` (human-readable)

### OBS-CM-03: Log Destination
- stdout (captured by AgentCore runtime logging)
- CloudWatch Log Group: `/disruptionai/constraint-matching-agent`
- Log retention: 90 days minimum (SECURITY-14 compliance)

### OBS-CM-04: Audit Trail Integration
- All funnel evaluations, planner decisions, and tracker updates written to Audit MCP (per BR-CM-14)
- Audit entries are the primary decision record; agent logs are supplementary

---

## Security Requirements (SECURITY Extension)

### SEC-CM-01: Input Validation (SECURITY-05)
- Agent validates all inputs from Orchestrator (order_id format, decision enum)
- MCP tool responses validated via Pydantic schemas before processing
- No raw LLM output used directly — all tool calls go through Strands SDK
- Revisit order_id validated against known order set

### SEC-CM-02: No Hardcoded Credentials (SECURITY-12)
- Bedrock credentials via IAM role (AgentCore managed runtime)
- MCP Gateway endpoint URL configurable via environment variable
- No API keys or secrets in source code

### SEC-CM-03: Least Privilege (SECURITY-06)
- Agent IAM role scoped to:
  - `bedrock:InvokeModel` on Claude 4.5 Haiku model ARN only
  - MCP tool access controlled by AgentCore Gateway authorization
- No direct DynamoDB access — all data access through MCP tools

### SEC-CM-04: Error Sanitization (SECURITY-09)
- Agent error messages to Orchestrator are generic — no stack traces or internal details
- Full error context logged server-side only
- LLM responses sanitized before presenting to Planner (no system prompt leakage)

### SEC-CM-05: Fail Closed (SECURITY-15)
- On unhandled exception: agent returns error to Orchestrator, does not proceed
- Global exception handler wraps agent entry point
- Tracker state already persisted is NOT rolled back on subsequent failure
- Cascade simulation timeout returns partial results (not a failure — graceful degradation)

---

## Scalability Requirements

### SCALE-CM-01: Order Volume
- MVP: 20 Florida orders per constraint matching run
- Funnel evaluation is O(1) per order (fixed 4 layers)
- Cascade simulation is O(n * d) where n = Ohio orders, d = cascade depth
- At MVP scale (20 Ohio orders, depth 5): ~100 iterations max — well within 3s timeout
- For future: scales to 200+ Florida orders without architectural change

### SCALE-CM-02: AgentCore Hosting
- Agent registered in Bedrock AgentCore managed runtime
- AgentCore handles scaling, health checks, and lifecycle
- Multi-session support via session-scoped trackers in DynamoDB

### SCALE-CM-03: Tracker Storage
- DynamoDB single-table design with session_id as partition key
- Each tracker record ~5-10 KB (20 processed orders + capacity state)
- TTL on tracker records: 24 hours (auto-cleanup of stale sessions)
