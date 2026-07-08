# Logical Components — Unit 1: ERP Data MCP Server

## Component Overview

```
MCP Tool Request
      |
      v
+------------------+
| MCP Transport    |  (stdio, handled by mcp SDK)
+------------------+
      |
      v
+------------------+
| Logging Layer    |  (log_tool_invocation decorator)
+------------------+
      |
      v
+------------------+
| Error Handler    |  (tool_error_handler decorator)
+------------------+
      |
      v
+------------------+
| Validation Layer |  (Pydantic input models)
+------------------+
      |
      v
+------------------+
| Tool Logic       |  (business logic per tool)
+------------------+
      |
      v
+------------------+
| DynamoDB Client  |  (singleton, retry config)
+------------------+
      |
      v
+------------------+
| DynamoDB Tables  |  (6 tables, On-Demand)
+------------------+
```

---

## Component 1: MCP Server (Entry Point)

- **Module**: `server.py`
- **Responsibility**: Initialize MCP server, register all 10 tools, start stdio transport
- **Dependencies**: mcp SDK, Settings, DynamoDBClient, all tool modules
- **Startup sequence**:
  1. Load Settings from environment
  2. Configure structured logging
  3. Initialize DynamoDB client singleton
  4. Register tool handlers with MCP server
  5. Start stdio transport loop

## Component 2: Settings Manager

- **Module**: `config.py`
- **Responsibility**: Load and validate configuration from environment variables
- **Pattern**: Pydantic BaseSettings (Pattern 5)
- **Validates at startup**: All required env vars present, valid values
- **Fails fast**: If configuration invalid, server exits with clear error message

## Component 3: Structured Logger

- **Module**: `logging/config.py`
- **Responsibility**: Configure JSON-formatted logging to stdout
- **Pattern**: Structured Logging Middleware (Pattern 3)
- **Fields**: timestamp, level, tool_name, correlation_id, duration_ms, message
- **Destination**: stdout (captured by ECS to CloudWatch)

## Component 4: DynamoDB Client

- **Module**: `db/client.py`
- **Responsibility**: Singleton boto3 DynamoDB resource with retry configuration
- **Pattern**: DynamoDB Client Singleton (Pattern 6)
- **Configuration**: Adaptive retry (4 attempts), 5s connect timeout, 10s read timeout
- **Table caching**: Table references cached after first access

## Component 5: Input Validation Models

- **Module**: `models/schemas.py`
- **Responsibility**: Pydantic models for all 10 tool input schemas
- **Pattern**: Pydantic Input Validation Layer (Pattern 4)
- **Models**: GetOrdersInput, GetOrderByIdInput, UpdateOrderPriorityInput, UpdateOrderStatusInput, GetMachineCapacityInput, GetMaterialsInput, GetCustomersInput, GetRunningTrackerInput, UpdateRunningTrackerInput
- **Note**: get_manpower has no input parameters (no model needed)

## Component 6: Tool Handlers (4 modules)

- **orders.py**: get_orders, get_order_by_id, update_order_priority, update_order_status
- **capacity.py**: get_machine_capacity, get_manpower, get_materials
- **customers.py**: get_customers
- **tracker.py**: get_running_tracker, update_running_tracker

Each handler applies decorator stack: `@mcp.tool() > @log_tool_invocation > @tool_error_handler`

## Component 7: Seed Data Loader

- **Module**: `db/seed.py`
- **Responsibility**: Load mock ERP data into DynamoDB tables
- **Invocation**: CLI command or startup flag (`--seed`)
- **Data**: 20 Florida orders, 20 Ohio orders, 10 customers, 2 machines, 1 manpower record, 3 materials
- **Idempotent**: Can be re-run without duplicating data (uses PutItem with overwrite)

---

## Cross-Cutting Concerns

| Concern | Component | Pattern |
|---------|-----------|---------|
| Retry | DynamoDB Client | Exponential backoff (Pattern 1) |
| Error handling | Tool Handler Wrapper | Decorator (Pattern 2) |
| Logging | Structured Logger | JSON middleware (Pattern 3) |
| Input validation | Pydantic Models | Schema enforcement (Pattern 4) |
| Configuration | Settings Manager | Environment variables (Pattern 5) |
| Connection management | DynamoDB Client | Singleton (Pattern 6) |
