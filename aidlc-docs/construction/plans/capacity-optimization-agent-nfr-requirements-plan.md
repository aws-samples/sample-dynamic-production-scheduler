# NFR Requirements Plan — Unit 5: Capacity & Optimization Agent

## Context
- **Unit**: Unit 5 — Capacity & Optimization Agent
- **Framework**: Strands Agents SDK (Python), same as Unit 4
- **Hosting**: Bedrock AgentCore managed runtime
- **MCP Access**: HTTP/SSE via AgentCore Gateway (ERP Data MCP + Audit MCP)
- **Functional Design**: 3 workflows (capacity analysis, constraint handling, delay optimization)

## Execution Steps

- [x] Step 1: Define NFR requirements (performance, reliability, observability, security, scalability)
- [x] Step 2: Define tech stack decisions

## Clarifying Questions

### Question 1: Capacity Analysis Performance Budget
Unit 5 makes more MCP calls than Unit 4 (6 data-fetch calls vs 2). What is the acceptable end-to-end time for the full capacity analysis?

A) 30 seconds (same as Unit 4 classification)
B) 45 seconds (more data fetching, more complex analysis)
C) 60 seconds (generous budget for 5-dimension analysis)
D) Other (please describe after [Answer]: tag below)

[Answer]: C

### Question 2: Delay Decision Response Time
After the planner approves/rejects a single delay candidate, how fast should the recalculation complete?

A) 5 seconds (fast feedback loop)
B) 10 seconds (same as Unit 4 reclassification)
C) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 3: Constraint Recalculation Time
After the planner adds a constraint (e.g., "No weekend shifts"), how fast should the before/after comparison appear?

A) 5 seconds (constraint application is simple math)
B) 10 seconds (includes LLM explanation generation)
C) Other (please describe after [Answer]: tag below)

[Answer]: B
