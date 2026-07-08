# Tech Stack Decisions — Unit 1: ERP Data MCP Server

## Runtime

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Language | Python 3.11+ | Strands Agents SDK compatibility, modern async support |
| Package Manager | pip + requirements.txt | Standard Python packaging, simple dependency management |
| Virtual Environment | venv | Built-in, no additional tooling required |

## MCP Framework

| Component | Decision | Rationale |
|-----------|----------|-----------|
| MCP Library | `mcp` (official Python SDK) | Official Model Context Protocol implementation |
| Transport | stdio | Standard for local MCP servers, subprocess communication |
| Tool Registration | Decorator-based (`@mcp.tool()`) | Clean, declarative tool definitions |

## AWS SDK

| Component | Decision | Rationale |
|-----------|----------|-----------|
| DynamoDB Client | boto3 | Official AWS SDK for Python |
| Retry Configuration | botocore Config with exponential backoff | Built-in retry support, configurable |
| Credential Provider | IAM task role (ECS) / environment (local) | No hardcoded credentials |

## DynamoDB Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Capacity Mode | On-Demand | Auto-scales, no capacity planning for MVP |
| Table Names | Environment variables | Configurable per environment |
| Region | Environment variable (AWS_REGION) | Deployment flexibility |

## Logging

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Library | Python `logging` | Built-in, no additional dependencies |
| Format | JSON (structlog or custom formatter) | Structured logs for CloudWatch parsing |
| Level | INFO (standard) | Tool invocations + errors + warnings |
| Output | stdout | ECS captures to CloudWatch Logs |

## Dependencies

```
# requirements.txt
boto3>=1.34.0
mcp>=1.0.0
pydantic>=2.0.0
python-json-logger>=2.0.0
```

| Dependency | Purpose |
|------------|---------|
| boto3 | AWS DynamoDB SDK |
| mcp | Model Context Protocol server |
| pydantic | Input validation and schema enforcement |
| python-json-logger | JSON log formatting |

## Configuration

Environment variables:
```
AWS_REGION=us-east-1
DYNAMODB_TABLE_ORDERS=disruptionai-orders
DYNAMODB_TABLE_CAPACITY=disruptionai-capacity
DYNAMODB_TABLE_MANPOWER=disruptionai-manpower
DYNAMODB_TABLE_MATERIALS=disruptionai-materials
DYNAMODB_TABLE_CUSTOMERS=disruptionai-customers
DYNAMODB_TABLE_TRACKER=disruptionai-tracker
LOG_LEVEL=INFO
```

## Project Structure

```
erp-data-mcp/
  src/
    erp_data_mcp/
      __init__.py
      server.py          # MCP server entry point
      tools/
        __init__.py
        orders.py        # get_orders, get_order_by_id, update_order_priority, update_order_status
        capacity.py      # get_machine_capacity, get_manpower, get_materials
        customers.py     # get_customers
        tracker.py       # get_running_tracker, update_running_tracker
      db/
        __init__.py
        client.py        # DynamoDB client with retry config
        tables.py        # Table name constants from env
      models/
        __init__.py
        schemas.py       # Pydantic models for validation
      logging/
        __init__.py
        config.py        # JSON logging setup
  tests/
    __init__.py
    test_orders.py
    test_capacity.py
    test_tracker.py
  requirements.txt
  README.md
```

