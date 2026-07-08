# Application Design Plan — DisruptionAI

## Purpose
Design high-level components, agent interfaces, tool definitions, and service layer orchestration for the 4-agent DisruptionAI system.

## Context
- **Architecture**: 4 agents (Orchestrator, Impact Assessment, Capacity & Optimization, Constraint Matching)
- **Framework**: Amazon Bedrock Claude via Strands Agents SDK
- **Compute**: ECS/Fargate (Python backend), Vite+React SPA (frontend)
- **Data**: DynamoDB for mock ERP data, separate audit storage
- **Streaming**: WebSocket API for real-time responses

---

## Application Design Questions

Please answer each question by filling in the letter choice after the [Answer]: tag.

### Question 1: Agent Tool Granularity
How granular should the agent tools be?

A) Coarse-grained — Few tools with broad capabilities (e.g., `analyze_capacity` does all 5 dimensions)
B) Fine-grained — Many small tools (e.g., `get_equipment_capability`, `get_machine_utilization`, `get_manpower`, etc.)
C) Hybrid — Coarse for queries, fine for mutations (e.g., `get_capacity_snapshot` but `update_order_priority`)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2: Shared Context Implementation
How should agents share context (prioritized orders, capacity snapshot)?

A) In-memory Python dict — Simple, fast, but lost on restart
B) DynamoDB table — Persistent, but adds latency (~5-10ms per read/write)
C) Hybrid — In-memory during session, persist to DynamoDB at checkpoints
X) Other (please describe after [Answer]: tag below)

[Answer]: Agentcore memory

### Question 3: Agent-to-Agent Communication Pattern
How should agents communicate with each other?

A) Direct invocation — Orchestrator calls agent functions directly (tight coupling)
B) Message passing — Agents publish/subscribe to shared context (loose coupling)
C) Tool-based — Orchestrator uses tools to invoke other agents (Strands SDK pattern)
X) Other (please describe after [Answer]: tag below)

[Answer]: Using MCP, and the pattern that works best for this architecture can be tool call, swarm etc

### Question 4: Running Capacity Tracker Location
Where should the running capacity tracker (updated after each order decision) live?

A) Frontend state — React manages tracker, sends to backend on each decision
B) Backend state — Python backend maintains tracker, streams updates to frontend
C) Shared context — Tracker in DynamoDB, both frontend and backend read/write
X) Other (please describe after [Answer]: tag below)

[Answer]: C

### Question 5: What-If Recalculation Scope
When Planner asks a what-if question (e.g., "What if I add weekend shifts?"), how much should be recalculated?

A) Full restart — Re-run all agents from Round 1 with modified parameters
B) Incremental — Only re-run affected agents (e.g., Capacity & Optimization Agent for shift changes)
C) Cached delta — Cache intermediate results, recalculate only the delta
X) Other (please describe after [Answer]: tag below)

[Answer]: Incremental

### Question 6: Frontend-Backend Boundary
Where should the approval/rejection logic live?

A) Frontend-heavy — React handles approval state, sends final decisions to backend
B) Backend-heavy — Backend manages all state, frontend is pure display
C) Split — Frontend manages UI state, backend manages business logic and persistence
X) Other (please describe after [Answer]: tag below)

[Answer]: split

---

## Execution Steps

After questions are answered, the following artifacts will be generated:

- [x] Step 1: Generate `components.md` — Component definitions and responsibilities
- [x] Step 2: Generate `component-methods.md` — Method signatures for each component
- [x] Step 3: Generate `services.md` — Service layer and orchestration patterns
- [x] Step 4: Generate `component-dependency.md` — Dependency relationships and data flow
- [x] Step 5: Generate `application-design.md` — Consolidated design document

---

## Notes
- Agent tool definitions will follow Strands Agents SDK patterns
- SECURITY extension rules will be considered in component design
- Design will support streaming responses via WebSocket
