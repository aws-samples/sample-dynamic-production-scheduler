# NFR Requirements Plan — Unit 1: ERP Data MCP Server

## Context
- **Unit**: ERP Data MCP Server
- **Type**: Data Access / MCP Server (Python)
- **Purpose**: Standardized access to mock ERP data in DynamoDB
- **Functional Design**: Complete (10 MCP tools, 6 DynamoDB tables, 19 business rules)

---

## NFR Requirements Questions

### Question 1: DynamoDB Capacity Mode
What DynamoDB capacity mode should be used for the ERP data tables?

A) On-Demand — Pay per request, auto-scales, no capacity planning (recommended for MVP/demo)
B) Provisioned — Fixed read/write capacity units, predictable cost, requires capacity planning
C) Provisioned with Auto-Scaling — Provisioned base with auto-scaling policies
X) Other (please describe after [Answer]: tag below)

[Answer]: on-demand

### Question 2: Error Retry Strategy
How should the MCP server handle transient DynamoDB errors?

A) No retry — Fail immediately and return error to caller (simplest, agents handle retry)
B) Simple retry — Retry up to 3 times with fixed 100ms delay
C) Exponential backoff — Retry with exponential backoff (100ms, 200ms, 400ms) up to 3 attempts
X) Other (please describe after [Answer]: tag below)

[Answer]: exponential 

### Question 3: Logging Level
What logging level should be configured for the MCP server?

A) Minimal — Errors only (smallest log volume)
B) Standard — Errors + warnings + tool invocations (recommended for debugging)
C) Verbose — All of B plus input/output payloads (useful for development, larger log volume)
X) Other (please describe after [Answer]: tag below)

[Answer]: standard

---

## Execution Steps

- [x] Step 1: Define performance requirements (response time, throughput)
- [x] Step 2: Define reliability requirements (error handling, retry strategy)
- [x] Step 3: Define observability requirements (logging, metrics)
- [x] Step 4: Select tech stack (Python version, DynamoDB SDK, MCP library)
- [x] Step 5: Generate NFR requirements and tech stack decision documents

