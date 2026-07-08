# Code Generation Plan — Unit 3: Audit MCP Server

## Context
Audit MCP Server follows the same architecture as Unit 1 (ERP Data MCP). 2 tools, DynamoDB-backed, stdio transport, Pydantic validation. Reuses decorators and db client patterns.

## Target Directory: `audit-mcp/`

## Steps

- [x] Step 1: Create project structure (pyproject.toml, requirements.txt, requirements-dev.txt)
- [x] Step 2: Create config.py (pydantic-settings, audit table name)
- [x] Step 3: Create logging_config.py (JSON structured logging)
- [x] Step 4: Create decorators.py (log_tool_invocation, tool_error_handler)
- [x] Step 5: Create db/client.py (DynamoDB singleton — reuse pattern from Unit 1)
- [x] Step 6: Create models/schemas.py (WriteAuditEntryInput, GetAuditTrailInput)
- [x] Step 7: Create tools/audit.py (write_audit_entry, get_audit_trail handlers)
- [x] Step 8: Create server.py (MCP server entry point, 2 tool registrations)
- [x] Step 9: Create tests/conftest.py (moto fixtures, audit table creation)
- [x] Step 10: Create tests/test_schemas.py (input validation tests)
- [x] Step 11: Create tests/test_audit.py (tool handler tests)
- [x] Step 12: Create tests/test_decorators.py (decorator tests)
- [x] Step 13: Create README.md
- [x] Step 14: Run all tests and verify
- [x] Step 15: Create code generation summary
