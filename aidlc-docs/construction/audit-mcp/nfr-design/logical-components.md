# Logical Components — Unit 3: Audit MCP Server

## Components

| Component | Type | Purpose |
|-----------|------|---------|
| MCP Server | Application | stdio transport server, tool registration |
| Audit Tool Handler | Application | write_audit_entry, get_audit_trail logic |
| Pydantic Schemas | Validation | Input validation models |
| DynamoDB Client | Data Access | Singleton client with retry (shared pattern) |
| Config | Configuration | pydantic-settings env-based config |
| Logging | Cross-cutting | JSON structured logging to stdout |
| Decorators | Cross-cutting | Error handling + invocation logging |

## Data Flow

```
Agent (caller)
    |
    | MCP tool call (stdio)
    v
+-------------------------------+
| Audit MCP Server              |
|  +-------------------------+  |
|  | Pydantic Validation     |  |
|  +-------------------------+  |
|           |                   |
|           v                   |
|  +-------------------------+  |
|  | Tool Handler            |  |
|  | (write / query)         |  |
|  +-------------------------+  |
|           |                   |
|           v                   |
|  +-------------------------+  |
|  | DynamoDB Client         |  |
|  +-------------------------+  |
+-------------------------------+
    |
    v
DynamoDB (audit table)
```
