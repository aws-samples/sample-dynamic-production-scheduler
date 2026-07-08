# Unit of Work Plan — DisruptionAI

## Purpose
Decompose DisruptionAI into manageable units of work for parallel development and structured implementation.

## Context
From Application Design, the system has 4 layers:
- Agent Layer (4 agents)
- Data Access Layer (3 MCP servers)
- Backend Services Layer (WebSocket Handler, Session Manager)
- Frontend Layer (React SPA)

---

## Unit of Work Questions

Please answer each question by filling in the letter choice after the [Answer]: tag.

### Question 1: Unit Granularity
How should the system be decomposed into units?

A) By layer — 4 units: Backend (agents + services), Frontend (React), Data (MCP servers + DynamoDB), Infrastructure (CDK)
B) By agent — 6 units: Orchestrator, Impact Assessment Agent, Capacity & Optimization Agent, Constraint Matching Agent, Frontend, Infrastructure
C) Coarse — 2 units: Backend (everything server-side), Frontend (React SPA)
X) Other (please describe after [Answer]: tag below)

[Answer]: by agent

### Question 2: MCP Server Packaging
How should the 3 MCP servers be packaged?

A) Single package — All 3 MCP servers in one Python package, deployed as sidecars to the main backend
B) Separate packages — Each MCP server is its own package, independently deployable
C) Embedded — MCP servers embedded in the main backend package (no separate deployment)
X) Other (please describe after [Answer]: tag below)

[Answer]: separate

### Question 3: Infrastructure Scope
What should the Infrastructure unit include?

A) Full CDK — VPC, ECS, API Gateway, DynamoDB, S3, CloudFront, IAM, CloudWatch
B) Minimal CDK — Only compute (ECS) and API Gateway; DynamoDB and S3 created manually or via console
C) Terraform — Use Terraform instead of CDK
X) Other (please describe after [Answer]: tag below)

[Answer]: full cdk

### Question 4: Development Sequence
In what order should units be developed?

A) Data-first — Data unit (MCP + DynamoDB) → Backend → Frontend → Infrastructure
B) Backend-first — Backend (agents) → Data → Frontend → Infrastructure
C) Infrastructure-first — Infrastructure → Data → Backend → Frontend
D) Parallel — All units developed in parallel with integration at the end
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Execution Steps

After questions are answered, the following artifacts will be generated:

- [x] Step 1: Generate `unit-of-work.md` — Unit definitions and responsibilities
- [x] Step 2: Generate `unit-of-work-dependency.md` — Dependency matrix between units
- [x] Step 3: Generate `unit-of-work-story-map.md` — Map user stories to units

---

## Notes
- Unit boundaries will align with deployment boundaries where possible
- Each unit will go through per-unit CONSTRUCTION stages (Functional Design, NFR, Code Generation)
- Story mapping ensures all 10 user stories are covered by units
