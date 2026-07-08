# NFR Requirements — Unit 1: ERP Data MCP Server

## Performance Requirements

### PERF-01: Tool Response Time
- Each MCP tool invocation must return within 500ms (p95)
- DynamoDB single-digit millisecond latency expected for all operations
- Seed data volume (40 orders, 10 customers, 3 materials, 2 machines) is small enough for consistent sub-100ms DynamoDB reads

### PERF-02: Throughput
- Single-user MVP — no concurrent request handling required
- Sequential tool invocations from agents (one at a time)
- No request queuing or rate limiting needed

### PERF-03: Startup Time
- MCP server must be ready to accept tool calls within 3 seconds of process start
- DynamoDB client initialization and connection pooling on startup

---

## Reliability Requirements

### REL-01: Error Retry Strategy
- Exponential backoff for transient DynamoDB errors
- Retry schedule: 100ms, 200ms, 400ms (3 attempts max)
- Retryable errors: ProvisionedThroughputExceededException, ThrottlingException, InternalServerError
- Non-retryable errors: ValidationException, ResourceNotFoundException, ConditionalCheckFailedException
- After max retries exhausted, return INTERNAL_ERROR to caller

### REL-02: Graceful Error Handling
- All tool handlers wrapped in try/except
- Consistent error response format (BR-15): `{"error": {"code": "...", "message": "..."}}`
- No unhandled exceptions propagated to MCP transport layer
- Input validation errors return immediately (no retry)

### REL-03: Data Consistency
- DynamoDB conditional writes for status transitions (BR-05)
- ConditionalCheckFailedException treated as INVALID_TRANSITION (not retried)
- Running tracker updates are idempotent where possible

---

## Observability Requirements

### OBS-01: Structured Logging
- Python `logging` module with JSON formatter
- Log level: Standard (errors + warnings + tool invocations)
- Every tool invocation logged: tool name, input parameters (excluding sensitive data), duration, success/failure
- Errors logged with full context: error code, message, stack trace

### OBS-02: Log Fields
Every log entry includes:
- `timestamp` (ISO 8601)
- `level` (ERROR, WARNING, INFO)
- `tool_name` (MCP tool being invoked)
- `correlation_id` (session_id when available)
- `duration_ms` (execution time)
- `message` (human-readable description)

### OBS-03: Log Destination
- stdout/stderr (captured by ECS/CloudWatch)
- CloudWatch Log Group: `/disruptionai/erp-data-mcp`
- Log retention: 90 days minimum (SECURITY-14 compliance)

### OBS-04: Metrics (Lightweight)
- Tool invocation count (logged, not custom CloudWatch metrics for MVP)
- Error count by error code (logged)
- DynamoDB retry count (logged)
- Custom CloudWatch metrics deferred to post-MVP

---

## Security Requirements (SECURITY Extension)

### SEC-01: Input Validation (SECURITY-05)
- All 10 MCP tools validate inputs before DynamoDB operations
- Regex validation for order_id (PO-YYYY-NNN) and customer_id (CUST-NNNN)
- Enum validation for plant, status, priority, machine_type, material_type, product_family
- No raw user input concatenated into DynamoDB queries (SDK handles parameterization)

### SEC-02: Error Sanitization (SECURITY-09)
- Error responses return generic messages — no stack traces, internal paths, or DynamoDB details
- INTERNAL_ERROR responses log full details server-side but return only "Internal server error" to caller

### SEC-03: No Hardcoded Credentials (SECURITY-12)
- AWS credentials via IAM task role (ECS) or environment (local dev)
- No AWS keys in source code or configuration files
- DynamoDB table names configurable via environment variables

### SEC-04: Least Privilege (SECURITY-06)
- IAM policy scoped to specific DynamoDB table ARNs
- Read-only actions: GetItem, Query, Scan on all 6 tables
- Write actions: UpdateItem on production_orders (priority, status only) and running_tracker
- No wildcard actions or resources

---

## Scalability Requirements

### SCALE-01: Data Volume
- 40 production orders (20 Florida + 20 Ohio)
- 10 customers
- 3 raw material types
- 2 machine types
- 1 manpower record
- Running tracker: 1 per session
- No pagination needed at this scale

### SCALE-02: DynamoDB Capacity
- On-Demand capacity mode (auto-scales, no capacity planning)
- Cost-effective for low-volume MVP workload
- No provisioned capacity tuning required

