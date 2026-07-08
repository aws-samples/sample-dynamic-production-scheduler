# ERP Data MCP Server

> **⚠️ Note:** This is a demo/sample component, not intended for production use without security review.

MCP server providing mock ERP data access for the DisruptionAI production scheduling system. Exposes 10 tools over stdio transport for querying and updating DynamoDB-backed production orders, capacity, materials, customers, and running tracker data.

## Tools

| Tool | Description |
|------|-------------|
| `get_orders` | Query orders by plant with optional status filter |
| `get_order_by_id` | Retrieve a single order by ID |
| `update_order_priority` | Set P1/P2/P3 priority (Florida orders only) |
| `update_order_status` | Update status with transition validation |
| `get_machine_capacity` | Query Rolling Mill or Finishing Line capacity (Ohio) |
| `get_workforce` | Query Ohio plant workforce availability |
| `get_materials` | Query raw material inventory with optional filter |
| `get_customers` | Query customer data with optional ID filter |
| `get_running_tracker` | Get capacity tracker for a workflow session |
| `update_running_tracker` | Update tracker after a scheduling decision |

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (for testing)
pip install -r requirements-dev.txt
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region |
| `DYNAMODB_TABLE_ORDERS` | `disruptionai-orders` | Orders table name |
| `DYNAMODB_TABLE_CAPACITY` | `disruptionai-capacity` | Capacity table name |
| `DYNAMODB_TABLE_WORKFORCE` | `disruptionai-workforce` | Workforce table name |
| `DYNAMODB_TABLE_MATERIALS` | `disruptionai-materials` | Materials table name |
| `DYNAMODB_TABLE_CUSTOMERS` | `disruptionai-customers` | Customers table name |
| `DYNAMODB_TABLE_TRACKER` | `disruptionai-tracker` | Tracker table name |
| `LOG_LEVEL` | `INFO` | Logging level |

## Running

```bash
# Start MCP server (stdio transport)
erp-data-mcp

# Seed DynamoDB tables with mock data
erp-data-mcp-seed
```

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
src/erp_data_mcp/
  server.py          # MCP server entry point + tool registration
  config.py          # Pydantic Settings (env-based config)
  logging_config.py  # JSON structured logging
  decorators.py      # Error handler + logging decorators
  db/client.py       # DynamoDB client singleton
  models/schemas.py  # Pydantic input validation models
  tools/             # Tool handlers (orders, capacity, customers, tracker)
  seed/              # Seed data definitions + loader
tests/               # Unit tests with moto DynamoDB mocks
```
