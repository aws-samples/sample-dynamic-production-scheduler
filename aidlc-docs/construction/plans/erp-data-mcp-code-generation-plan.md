# Code Generation Plan — Unit 1: ERP Data MCP Server

## Unit Context

- **Unit**: ERP Data MCP Server
- **Role**: MCP server providing 10 tools for DynamoDB-backed mock ERP data access
- **Transport**: stdio (subprocess within ECS task)
- **Stories Supported**: US-02, US-03, US-04, US-06, US-07, US-08, US-09 (all as supporting unit)
- **Dependencies**: None (first unit in build sequence)
- **Consumers**: Unit 4 (Impact Assessment Agent), Unit 5 (Capacity & Optimization Agent), Unit 6 (Constraint Matching Agent)

## Target Project Structure

```
erp-data-mcp/
  src/
    erp_data_mcp/
      __init__.py
      server.py              # MCP server entry point + tool registration
      config.py              # Pydantic Settings (env-based config)
      logging_config.py      # JSON structured logging setup
      decorators.py          # log_tool_invocation + tool_error_handler
      db/
        __init__.py
        client.py            # DynamoDB client singleton
      models/
        __init__.py
        schemas.py           # Pydantic input validation models
      tools/
        __init__.py
        orders.py            # get_orders, get_order_by_id, update_order_priority, update_order_status
        capacity.py          # get_machine_capacity, get_manpower, get_materials
        customers.py         # get_customers
        tracker.py           # get_running_tracker, update_running_tracker
      seed/
        __init__.py
        loader.py            # Seed data loader (CLI entry point)
        data.py              # Seed data definitions (orders, capacity, materials, customers, manpower)
  tests/
    __init__.py
    conftest.py              # Shared fixtures (mocked DynamoDB, settings)
    test_orders.py           # Tests for order tools
    test_capacity.py         # Tests for capacity/manpower/materials tools
    test_customers.py        # Tests for customer tools
    test_tracker.py          # Tests for running tracker tools
    test_decorators.py       # Tests for error handler + logging decorators
    test_schemas.py          # Tests for Pydantic validation models
  requirements.txt
  requirements-dev.txt
  pyproject.toml
  README.md
```

## Code Location

- **Application Code**: `erp-data-mcp/` (workspace root)
- **Documentation**: `aidlc-docs/construction/erp-data-mcp/code/` (markdown summaries only)

---

## Execution Steps

### Step 1: Project Structure Setup
- [x] Create `erp-data-mcp/` directory structure
- [x] Create `pyproject.toml` with package metadata and entry points
- [x] Create `requirements.txt` (runtime dependencies: boto3, mcp, pydantic, pydantic-settings, python-json-logger)
- [x] Create `requirements-dev.txt` (dev dependencies: pytest, pytest-asyncio, moto)
- [x] Create all `__init__.py` files

### Step 2: Configuration Module
- [x] Create `config.py` — Pydantic BaseSettings with all env vars (Pattern 5)
- [x] Validates: AWS_REGION, 6 table names, LOG_LEVEL
- [x] Defaults for local development

### Step 3: Logging Module
- [x] Create `logging_config.py` — JSON structured logging to stdout (Pattern 3)
- [x] Fields: timestamp, level, name, message
- [x] Configurable log level from Settings

### Step 4: DynamoDB Client Module
- [x] Create `db/client.py` — Singleton DynamoDB resource (Pattern 6)
- [x] Adaptive retry config (4 attempts), connect timeout 5s, read timeout 10s
- [x] Table reference caching

### Step 5: Pydantic Input Validation Models
- [x] Create `models/schemas.py` — All input models (Pattern 4)
- [x] Models: GetOrdersInput, GetOrderByIdInput, UpdateOrderPriorityInput, UpdateOrderStatusInput, GetMachineCapacityInput, GetMaterialsInput, GetCustomersInput, GetRunningTrackerInput, UpdateRunningTrackerInput
- [x] Regex patterns for order_id (PO-YYYY-NNN), customer_id (CUST-NNNN), session_id (UUID v4)
- [x] Enum constraints for plant, status, priority, machine_type, material_type

### Step 6: Decorators Module
- [x] Create `decorators.py` — log_tool_invocation + tool_error_handler (Patterns 2, 3)
- [x] Error mapping: ValidationError→INVALID_INPUT, ConditionalCheckFailed→INVALID_TRANSITION, ResourceNotFound→NOT_FOUND, ClientError→INTERNAL_ERROR
- [x] Timing + structured log entries per invocation

### Step 7: Order Tools
- [x] Create `tools/orders.py` — 4 tool handlers
- [x] `get_orders`: Query by plant + optional status using GSI (BR-02, BR-18)
- [x] `get_order_by_id`: GetItem by order_id (BR-01)
- [x] `update_order_priority`: Update priority with Florida-only check (BR-04)
- [x] `update_order_status`: Update status with transition validation using conditional writes (BR-05, BR-16)

### Step 8: Capacity Tools
- [x] Create `tools/capacity.py` — 3 tool handlers
- [x] `get_machine_capacity`: GetItem by machine_type + Ohio (BR-06, BR-07)
- [x] `get_manpower`: GetItem for Ohio manpower (BR-06)
- [x] `get_materials`: Query materials with optional filter (BR-08, BR-18)

### Step 9: Customer Tools
- [x] Create `tools/customers.py` — 1 tool handler
- [x] `get_customers`: Query with optional customer_id filter (BR-12, BR-18)

### Step 10: Tracker Tools
- [x] Create `tools/tracker.py` — 2 tool handlers
- [x] `get_running_tracker`: GetItem by session_id (BR-14)
- [x] `update_running_tracker`: Partial update with non-negative validation, create-if-not-exists (BR-09, BR-10)

### Step 11: MCP Server Entry Point
- [x] Create `server.py` — Initialize MCP server, register all 10 tools, start stdio transport
- [x] Startup: Settings → Logging → DynamoDB client → Register tools → Start transport
- [x] CLI entry point via `__main__.py` or pyproject.toml script

### Step 12: Seed Data Module
- [x] Create `seed/data.py` — All seed data definitions
- [x] 20 Florida orders (8 urgent, 7 mid-range, 5 long-term; edge cases per business-logic-model.md)
- [x] 20 Ohio orders (5 delay candidates, 10 mid-range, 5 near-deadline; edge cases per business-logic-model.md)
- [x] 2 machine capacity records (Rolling Mill + Finishing Line with compatibility matrix)
- [x] 1 manpower record (45 total, 38 allocated, 7 surplus)
- [x] 3 raw material records (Hot-Rolled Coil, Steel Slab, Steel Billet)
- [x] 10 customer records (3 Tier1, 4 Tier2, 3 Tier3; penalty clauses per business-logic-model.md)
- [x] Create `seed/loader.py` — BatchWriteItem loader with idempotent PutItem

### Step 13: Unit Tests — Schemas
- [x] Create `tests/test_schemas.py`
- [x] Valid input acceptance for all models
- [x] Invalid input rejection (bad patterns, invalid enums, missing required fields)
- [x] Edge cases: boundary values, empty strings, null handling

### Step 14: Unit Tests — Decorators
- [x] Create `tests/test_decorators.py`
- [x] Error handler maps exceptions to correct error codes
- [x] Logging decorator captures timing and tool name
- [x] Unexpected exceptions return INTERNAL_ERROR (no stack trace leak)

### Step 15: Unit Tests — Order Tools
- [x] Create `tests/test_orders.py` using moto DynamoDB mock
- [x] get_orders: by plant, by plant+status, empty results
- [x] get_order_by_id: found, not found, invalid ID format
- [x] update_order_priority: valid update, Florida-only check, invalid priority
- [x] update_order_status: valid transitions, invalid transitions (terminal states), conditional write failure

### Step 16: Unit Tests — Capacity Tools
- [x] Create `tests/test_capacity.py` using moto DynamoDB mock
- [x] get_machine_capacity: Rolling Mill, Finishing Line
- [x] get_manpower: returns Ohio data
- [x] get_materials: all materials, filtered by type, not found

### Step 17: Unit Tests — Customer Tools
- [x] Create `tests/test_customers.py` using moto DynamoDB mock
- [x] get_customers: all customers, filtered by ID, not found

### Step 18: Unit Tests — Tracker Tools
- [x] Create `tests/test_tracker.py` using moto DynamoDB mock
- [x] get_running_tracker: found, not found
- [x] update_running_tracker: create new, partial update, non-negative validation, add to order lists

### Step 19: Shared Test Fixtures
- [x] Create `tests/conftest.py` — moto DynamoDB fixtures, Settings override, seed data helper

### Step 20: README and Documentation
- [x] Create `erp-data-mcp/README.md` — Setup, usage, tool reference, local development
- [x] Create `aidlc-docs/construction/erp-data-mcp/code/code-generation-summary.md` — Summary of generated code

---

## Story Traceability

| Step | Stories Supported |
|------|-------------------|
| Steps 7, 15 (Orders) | US-02, US-03, US-07, US-08 |
| Steps 8, 16 (Capacity) | US-04, US-06, US-07 |
| Steps 9, 17 (Customers) | US-02, US-07 |
| Steps 10, 18 (Tracker) | US-06, US-07, US-08, US-09 |
| Step 12 (Seed Data) | All supported stories (data foundation) |

## Security Compliance Notes

- SECURITY-03: Structured logging with no PII/secrets in logs (Steps 3, 6)
- SECURITY-05: Pydantic input validation on all tools (Step 5)
- SECURITY-06: Least-privilege IAM documented in infrastructure design (CDK Unit 9)
- SECURITY-09: No hardcoded credentials, env-based config (Step 2)
- SECURITY-10: Pinned dependencies in requirements.txt (Step 1)
- SECURITY-12: No hardcoded credentials in source (Step 2)
- SECURITY-15: Global error handler via decorator, fail-closed, resource cleanup (Step 6)
