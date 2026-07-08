# NFR Requirements Plan — Unit 6: Constraint Matching Agent

## Context
- **Unit**: Unit 6 — Constraint Matching Agent
- **Language**: Python (Strands Agents SDK)
- **Stories**: US-07, US-08, US-09
- **Dependencies**: Unit 1 (ERP Data MCP), Unit 3 (Audit MCP), Unit 5 (shared context)
- **Prior NFR patterns**: Units 4 and 5 establish the agent NFR baseline

## Execution Steps

- [x] Step 1: Define NFR requirements (performance, reliability, observability, security, scalability)
- [x] Step 2: Define tech stack decisions

## Questions

## Question 1: Per-Order Funnel Latency Budget
The agent processes orders one at a time through a 4-layer funnel. What is the acceptable latency per order?

A) 5 seconds per order (tight — minimal LLM reasoning per layer)
B) 10 seconds per order (balanced — allows natural language explanation per layer)
C) 15 seconds per order (generous — allows deep cascade simulation + detailed explanation)
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 2: Running Tracker Persistence Frequency
The tracker is persisted to DynamoDB via ERP Data MCP after each decision. Should there be a write-back optimization?

A) Write after every decision (current design — most durable, ~100-300ms per write)
B) Write after every 3 decisions (batch — reduces DynamoDB calls, risk of losing 1-2 decisions on crash)
C) Write after every decision + periodic checkpoint every 5 minutes (belt and suspenders)
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 3: Cascade Simulation Timeout
Layer 4 multi-level cascade simulation could be expensive for deep cascades. Should there be a timeout?

A) No timeout — always simulate to max_cascade_depth (default 5 levels)
B) 3-second timeout — if cascade simulation exceeds 3s, return results computed so far with warning
C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 4: Concurrent Session Handling
Should the agent support multiple planners running constraint matching simultaneously?

A) Single session only (MVP — one planner at a time, simplest tracker management)
B) Multiple sessions with session-scoped trackers (each planner gets independent tracker)
C) Other (please describe after [Answer]: tag below)

[Answer]: B
