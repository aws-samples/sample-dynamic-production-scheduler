# Business Logic Model — Unit 7: Orchestrator Agent

## Overview

The Orchestrator Agent is the top-level coordinator for the DisruptionAI workflow. It manages the conversation with the Production Planner, invokes sub-agents as Strands tools backed by AgentCore managed runtime, coordinates the two-round disruption response, handles what-if recalculations, and generates workflow summaries. It does not contain domain-specific business logic — it delegates to specialist agents and synthesizes their outputs.

---

## Workflow State Machine

```
IDLE --> DISRUPTION_DETECTED --> ROUND1_IN_PROGRESS --> ROUND1_COMPLETE
  --> ROUND2_DELAYS --> ROUND2_FUNNEL --> SUMMARY --> COMPLETE
```

At any point during ROUND1_COMPLETE, ROUND2_DELAYS, or ROUND2_FUNNEL, the Planner can trigger a WHAT_IF detour, which returns to the previous phase after resolution.

---

## Phase 1: Disruption Detection (US-01)

### Trigger
Planner sends a message describing a disruption event (e.g., "A tornado is approaching the Florida plant").

### Logic
1. Orchestrator LLM analyzes the message for disruption intent
2. If disruption detected, extract: event_type, affected_plant, description
3. Create `DisruptionEvent` entity
4. Present confirmation to Planner:
   "I understand a [event_type] is affecting the [plant] plant. Shall I begin the disruption response workflow?"
5. On Planner confirmation, transition to ROUND1_IN_PROGRESS
6. Write `workflow_started` audit entry

### Non-Disruption Messages
- If Planner sends a non-disruption message while IDLE, Orchestrator responds conversationally
- Orchestrator can answer general questions about the system, explain the workflow, etc.
- No sub-agents are invoked until a disruption is confirmed

---

## Phase 2: Round 1 — Parallel Intelligence Gathering

### Trigger
Planner confirms disruption event.

### Logic
1. Transition session to ROUND1_IN_PROGRESS
2. Write `round1_started` audit entry
3. Orchestrator LLM invokes Impact Assessment Agent tool:
   - Input: "Analyze and prioritize all active Florida orders for the [event_type] disruption"
   - Agent scores and classifies orders as P1/P2/P3
   - Agent writes `prioritized_orders` to AgentCore Memory
   - Response streamed to Planner
4. Orchestrator LLM invokes Capacity & Optimization Agent tool:
   - Input: "Analyze Ohio plant capacity across all 5 dimensions for absorbing Florida orders"
   - Agent calculates equipment, utilization, manpower, materials, existing load
   - Agent writes `capacity_snapshot` to AgentCore Memory
   - Response streamed to Planner
5. After both tools complete, Orchestrator LLM generates combined Round 1 summary
6. Transition to ROUND1_COMPLETE
7. Write `round1_completed` audit entry
8. Present summary and ask: "Ready to proceed to Round 2 (delay optimization and constraint matching)?"

### Error Handling
- If Impact Assessment Agent fails after retry: present error, offer to proceed without priorities
- If Capacity Agent fails after retry: present error, offer to proceed with priorities only
- If both fail: halt workflow, explain to Planner, offer to retry

---

## Phase 3: Round 2, Step 1 — Delay Optimization

### Trigger
Planner confirms readiness for Round 2.

### Logic
1. Transition session to ROUND2_DELAYS
2. Write `round2_started` audit entry with phase="delays"
3. Orchestrator LLM invokes Capacity & Optimization Agent tool:
   - Input: "Identify Ohio delay candidates (P3 orders with deadline > 6 weeks) and present each for Planner approval"
   - Agent identifies candidates and presents them one at a time
   - For each candidate, agent streams recommendation to Planner via Orchestrator
   - Planner approves/rejects each delay through the conversation
   - Agent recalculates capacity after all decisions
   - Agent writes updated `capacity_snapshot` to AgentCore Memory
4. After all delay decisions, Orchestrator confirms delay phase complete
5. Transition to ROUND2_FUNNEL

### Planner Interaction
- Each delay candidate is presented with: order details, freed capacity if delayed, impact on Ohio schedule
- Planner responds with approve/reject for each
- Planner can say "skip remaining" to end delay phase early

---

## Phase 4: Round 2, Step 2 — Constraint Funnel

### Trigger
Delay phase complete (all candidates processed or Planner skipped).

### Logic
1. Transition session to ROUND2_FUNNEL
2. Orchestrator LLM invokes Constraint Matching Agent tool:
   - Input: "Run the 4-layer constraint funnel for all Florida orders in priority order (P1 first)"
   - Agent reads prioritized_orders and updated capacity_snapshot from AgentCore Memory
   - For each Florida order, agent runs 4-layer funnel and presents recommendation
   - Planner approves/rejects/skips each order through the conversation
   - Agent updates running capacity tracker after each decision
3. After all orders processed (or Planner ends early), transition to SUMMARY
4. Write `round2_completed` audit entry with decision counts

### Planner Interaction
- Each order recommendation includes: funnel results (4 layers), recommendation (reroute/defer), reasoning
- Planner responds with approve/reject/skip
- Planner can ask what-if questions at any point (triggers BR-OA-06)
- Planner can say "skip remaining orders" to end funnel early

---

## Phase 5: What-If Recalculation (US-05)

### Trigger
Planner asks a what-if question during Round 1 review, Round 2 delays, or Round 2 funnel.

### Logic
1. Orchestrator LLM analyzes the what-if question
2. LLM determines affected agent(s):
   - Capacity-related questions (shifts, overtime, equipment) -> Capacity & Optimization Agent
   - Priority-related questions (weights, thresholds) -> Impact Assessment Agent
   - Constraint-related questions (material lead times, machine compatibility) -> Constraint Matching Agent
3. Orchestrator invokes affected agent(s) with modified parameters
4. If capacity changes, downstream constraint matching is re-triggered for the current order
5. Results streamed to Planner with comparison to previous state
6. Write `what_if_requested` and `what_if_completed` audit entries
7. Return to previous phase

### Examples
- "What if I add weekend shifts?" -> Capacity Agent recalculates with weekend shifts enabled
- "What if we lower the P1 threshold to 65?" -> Impact Agent reclassifies with new threshold
- "What if material lead time is 2 weeks instead of 4?" -> Constraint Agent re-evaluates current order

---

## Phase 6: Summary Generation

### Trigger
All Round 2 orders processed or Planner ends workflow.

### Logic
1. Transition session to SUMMARY
2. Orchestrator LLM generates plain-language summary using conversation context:
   - Total Florida orders analyzed
   - Priority distribution (P1/P2/P3 counts)
   - Ohio delays approved/rejected
   - Orders rerouted/deferred/skipped
   - Final capacity utilization
   - Key decisions and their rationale
   - What-if scenarios explored
3. Present summary to Planner
4. Write `workflow_completed` audit entry
5. Transition to COMPLETE

---

## Agent Tool Definitions

The Orchestrator exposes three sub-agent tools to its Strands LLM:

| Tool Name | AgentCore Agent | Purpose |
|-----------|----------------|---------|
| `invoke_impact_assessment` | Unit 4 agent ID | Prioritize Florida orders |
| `invoke_capacity_optimization` | Unit 5 agent ID | Analyze Ohio capacity, manage delays |
| `invoke_constraint_matching` | Unit 6 agent ID | Run 4-layer constraint funnel |

Each tool:
- Accepts a text prompt (instruction for the sub-agent)
- Invokes the sub-agent via AgentCore managed runtime API
- Returns the sub-agent's text response
- Handles retry on failure (BR-OA-08)

Additionally, the Orchestrator has direct MCP tool access:

| MCP Server | Tool | Purpose |
|------------|------|---------|
| Audit MCP | `write_audit_entry` | Log workflow-level events |
| Audit MCP | `get_audit_trail` | Retrieve session audit history |

---

## System Prompt Strategy

The Orchestrator's system prompt guides the LLM through the workflow:

1. Role definition: "You are the DisruptionAI Orchestrator coordinating a production disruption response"
2. Workflow phases: Describe the Round 1 -> Round 2 -> Summary flow
3. Tool usage instructions: When to invoke each sub-agent and what to pass
4. Planner interaction rules: Always wait for confirmation, never decide for the Planner
5. What-if handling: How to analyze questions and route to appropriate agents
6. Summary format: Structure for the final workflow summary
7. Error handling: What to do when sub-agents fail

The system prompt is the primary mechanism for controlling workflow behavior — the Orchestrator has minimal hardcoded logic beyond session state tracking and tool definitions.

---

## Shared Context Coordination

```
Round 1:
  Impact Assessment Agent --> AgentCore Memory: "prioritized_orders"
  Capacity & Optimization Agent --> AgentCore Memory: "capacity_snapshot"

Round 2 (Delays):
  Capacity & Optimization Agent --> AgentCore Memory: updated "capacity_snapshot"

Round 2 (Funnel):
  Constraint Matching Agent <-- AgentCore Memory: reads "prioritized_orders" + "capacity_snapshot"
  Constraint Matching Agent --> ERP Data MCP: updates running_tracker

What-If:
  Affected Agent --> AgentCore Memory: updates relevant key
  Downstream Agent <-- AgentCore Memory: reads updated context
```

The Orchestrator does not directly read/write shared context keys (except `workflow_session`). Sub-agents manage their own shared context reads and writes.
