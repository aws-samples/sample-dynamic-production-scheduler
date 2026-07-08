# NFR Requirements Plan — Unit 4: Impact Assessment Agent

## Purpose
Determine non-functional requirements and tech stack for the Impact Assessment Agent — a Strands Agents SDK agent that scores and classifies Florida production orders.

## Context
- **Unit**: Unit 4 — Impact Assessment Agent
- **Type**: AI Agent (Strands Agents SDK + Bedrock Claude)
- **Runtime**: Python, invoked by Orchestrator Agent
- **MCP Consumption**: Calls ERP Data MCP and Audit MCP tools (FastMCP, hosted on AgentCore Gateway)
- **Functional Design**: Complete (business-logic-model.md, business-rules.md, domain-entities.md)

## NFR Questions

### Question 1: Agent Hosting Model
How will the Impact Assessment Agent be deployed?

A) Standalone container (ECS Fargate) — agent runs as its own service
B) AgentCore managed runtime — agent registered and hosted via Bedrock AgentCore
C) Embedded in Orchestrator — agent code runs in-process within the Orchestrator container
D) Lambda function — agent invoked per-request as a Lambda
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 2: LLM Model Selection
Which Bedrock model should the agent use for reasoning?

A) Claude 3.5 Sonnet — balanced cost/quality for production
B) Claude 3 Haiku — fastest/cheapest, good for structured scoring tasks
C) Claude 3.5 Haiku — fast and cheap with better reasoning than Haiku
D) Configurable — default to Claude 3.5 Sonnet, allow override via environment variable
X) Other (please describe after [Answer]: tag below)

[Answer]: Claude 4.5 haiku

### Question 3: Agent Response Time Budget
What is the acceptable end-to-end time for the full priority classification run (20 Florida orders)?

A) Under 10 seconds — fast, may require parallel MCP calls
B) Under 30 seconds — reasonable for batch scoring
C) Under 60 seconds — relaxed, sequential processing fine
D) No hard limit — Planner expects to wait for a thorough analysis
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 4: MCP Tool Access Pattern
How does the agent connect to MCP servers on AgentCore Gateway?

A) HTTP/SSE — agent calls MCP tools via HTTP endpoints on AgentCore Gateway
B) Stdio subprocess — agent spawns MCP servers as local subprocesses
C) AgentCore SDK built-in — Strands SDK handles MCP tool routing through AgentCore
D) WebSocket — persistent connection to MCP gateway
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Execution Steps

After questions are answered:

- [x] Step 1: Generate `nfr-requirements.md` — Performance, reliability, security, observability requirements
- [x] Step 2: Generate `tech-stack-decisions.md` — Runtime, framework, model, dependency decisions
