# Infrastructure Design Plan — Unit 1: ERP Data MCP Server

## Context
- **Unit**: ERP Data MCP Server
- **Deployment**: Python subprocess (stdio transport), runs alongside agents on ECS
- **Infrastructure Needs**: DynamoDB tables, IAM policies, CloudWatch log group
- **No standalone compute**: MCP server is a subprocess, not an independent service

---

## Infrastructure Design Questions

### Question 1: DynamoDB Table Naming Convention
What naming convention should be used for DynamoDB tables?

A) Environment prefix — `{env}-disruptionai-{table}` (e.g., dev-disruptionai-orders)
B) Project prefix — `disruptionai-{table}` (e.g., disruptionai-orders)
C) Stack-based — CDK auto-generates with stack prefix and random suffix
X) Other (please describe after [Answer]: tag below)

[Answer]: project-prefix

### Question 2: DynamoDB Deletion Protection
Should DynamoDB tables have deletion protection enabled?

A) Yes — Prevent accidental deletion (recommended for production, adds friction for dev cleanup)
B) No — Allow easy teardown for MVP/demo environment
X) Other (please describe after [Answer]: tag below)

[Answer]: no

---

## Execution Steps

- [x] Step 1: Design DynamoDB table infrastructure (6 tables with GSIs)
- [x] Step 2: Design IAM policy for MCP server (least-privilege)
- [x] Step 3: Design CloudWatch log group configuration
- [x] Step 4: Generate infrastructure design artifacts
