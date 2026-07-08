# Functional Design Plan — Unit 7: Orchestrator Agent

## Context
- **Unit**: Unit 7 — Orchestrator Agent
- **Language**: Python 3.11+ (Strands Agents SDK)
- **Primary Stories**: US-01 (Disruption Alert), US-05 (Planner Constraints)
- **Supporting Stories**: US-03 (Reclassification routing), US-08 (Decision routing), US-10 (Streaming coordination)
- **Dependencies**: Units 4 (Impact Assessment), 5 (Capacity & Optimization), 6 (Constraint Matching), 3 (Audit MCP)

## Execution Steps

- [x] Step 1: Define domain entities and data models (domain-entities.md)
- [x] Step 2: Define business rules (business-rules.md)
- [x] Step 3: Define business logic model — workflow orchestration (business-logic-model.md)

## Questions

The following questions need answers before generating functional design artifacts.

## Question 1: Sub-Agent Invocation Pattern
How should the Orchestrator invoke sub-agents (Units 4, 5, 6)?

A) Direct Python function call — Orchestrator imports and calls `create_agent()` + `run_agent()` from each sub-agent package, all in the same process
B) Strands Agent-as-Tool — Each sub-agent is wrapped as a Strands `@tool` that the Orchestrator's LLM can call, with the LLM deciding when to invoke each agent
C) Hybrid — Round 1 agents (Impact Assessment + Capacity) are called programmatically in parallel (Python asyncio), Round 2 agents are exposed as tools for LLM-driven interactive flow
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2: Round 1 Parallel Execution Mechanism
How should the Orchestrator execute Impact Assessment and Capacity & Optimization agents in parallel during Round 1?

A) Python asyncio — `asyncio.gather()` with both agent calls as coroutines
B) Python threading — `concurrent.futures.ThreadPoolExecutor` with both agents as callables
C) Sequential with fast execution — Run one after the other (simpler, acceptable if each completes in < 3s)
D) Other (please describe after [Answer]: tag below)

[Answer]: Other - Agentcore runtime

## Question 3: Shared Context Mechanism
How should agents share context (prioritized orders, capacity snapshot) between rounds?

A) AgentCore Memory (AWS managed) — Agents read/write via AgentCore Memory SDK calls
B) In-process Python dict — Module-level shared state (simplest for single-process deployment)
C) DynamoDB via ERP Data MCP — Write/read shared context through MCP tools
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4: What-If Recalculation Scope
When the Planner asks a what-if question (e.g., "What if I add weekend shifts?"), how should the Orchestrator determine which agents to re-invoke?

A) LLM-driven routing — The Orchestrator LLM analyzes the question and decides which agent(s) to call
B) Keyword-based routing — Pattern match on keywords (e.g., "capacity" → Capacity Agent, "priority" → Impact Agent)
C) Always re-invoke all affected downstream agents — Conservative approach, re-run from the affected point forward
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5: Session and Conversation State
How should the Orchestrator manage conversation state across the multi-round workflow?

A) Strands Agent built-in conversation history — Let the LLM's context window hold the full conversation
B) Explicit session object — Python dataclass tracking current phase, completed rounds, decisions made
C) Hybrid — Strands conversation history for LLM context + explicit session object for programmatic state tracking
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 6: Disruption Detection (US-01) — MVP Approach
The Builder Spec mentions a mock weather API. For MVP, how should disruption detection work?

A) Planner manually triggers — Planner types "A tornado is approaching the Florida plant" and Orchestrator recognizes intent
B) Mock weather MCP tool — Orchestrator calls Weather MCP `get_active_events()` on startup and alerts if events found
C) Hardcoded scenario — Orchestrator always starts with the tornado scenario, no detection needed
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7: Streaming Coordination
How should the Orchestrator relay streaming tokens from sub-agents to the frontend?

A) Pass-through — Sub-agent tokens stream directly through the Orchestrator's Strands callback to WebSocket
B) Buffered relay — Orchestrator collects sub-agent output, then streams its own summary to frontend
C) Hybrid — Sub-agent structured data (tables) sent as complete payloads, natural language streamed token-by-token
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 8: Error Recovery Between Rounds
If a sub-agent fails during execution, how should the Orchestrator handle it?

A) Retry once, then fail the entire workflow with explanation to Planner
B) Retry once, then continue with partial results (e.g., if Capacity Agent fails but Impact Agent succeeded, present partial Round 1)
C) No retry — fail immediately and inform Planner
D) Other (please describe after [Answer]: tag below)

[Answer]: B
