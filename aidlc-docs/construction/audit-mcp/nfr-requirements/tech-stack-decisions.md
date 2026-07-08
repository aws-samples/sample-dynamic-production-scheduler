# Tech Stack Decisions — Unit 3: Audit MCP Server

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.11+ | Consistent with Unit 1, Strands SDK ecosystem |
| MCP Framework | mcp (PyPI) | Same as Unit 1 |
| Transport | stdio | Same as Unit 1 — subprocess alongside agents |
| Validation | Pydantic v2 | Same as Unit 1 |
| Config | pydantic-settings | Same as Unit 1 |
| Data Store | DynamoDB | Same as Unit 1, separate audit table |
| Testing | pytest + moto | Same as Unit 1 |
| Logging | Python logging (JSON) | Same as Unit 1 |
