# Infrastructure Design Plan — Unit 4: Impact Assessment Agent

## Purpose
Map the Impact Assessment Agent's logical components to actual AWS infrastructure services.

## Context
- **Unit**: Unit 4 — Impact Assessment Agent
- **Hosting**: Bedrock AgentCore managed runtime
- **LLM**: Claude 4.5 Haiku (Bedrock)
- **MCP Access**: HTTP/SSE to FastMCP servers on AgentCore Gateway
- **Data Stores**: None owned — all data via MCP tools

## Execution Steps

- [x] Step 1: Generate `infrastructure-design.md` — AWS services, IAM, logging
- [x] Step 2: Generate `deployment-architecture.md` — AgentCore deployment model, environment config
