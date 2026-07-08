# NFR Design Patterns — Unit 3: Audit MCP Server

## Pattern 1: Structured Logging (same as Unit 1)
- JSON structured logging to stdout
- Fields: timestamp, level, tool name, duration_ms, correlation
- No PII or secrets in log output

## Pattern 2: Input Validation Gate (same as Unit 1)
- Pydantic v2 models validate all tool inputs before processing
- Fail-fast on invalid input with INVALID_INPUT error code

## Pattern 3: Error Handler Decorator (same as Unit 1)
- `@tool_error_handler` catches all exceptions
- Maps to standardized error codes (INVALID_INPUT, NOT_FOUND, INTERNAL_ERROR)
- Never leaks stack traces or internal details

## Pattern 4: Invocation Logging Decorator (same as Unit 1)
- `@log_tool_invocation` logs tool name, duration_ms, success/failure
- Wraps all tool handlers

## Pattern 5: Immutable Append-Only Storage
- Audit entries are write-once, never updated or deleted
- DynamoDB table has no update/delete operations exposed
- Supports SECURITY-14 log integrity requirements

## Pattern 6: DynamoDB Client Singleton (reuse from Unit 1)
- Shared `DynamoDBClient` singleton with adaptive retry
- Same pattern as erp-data-mcp db/client.py
