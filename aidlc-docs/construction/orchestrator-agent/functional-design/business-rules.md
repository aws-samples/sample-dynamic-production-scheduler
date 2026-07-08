# Business Rules — Unit 7: Orchestrator Agent

## BR-OA-01: Disruption Detection (MVP)

- Orchestrator does NOT auto-detect disruptions — Planner manually describes the event
- Orchestrator uses LLM intent detection to recognize disruption-related messages
- Recognized intents: natural disaster, plant shutdown, supply chain disruption, equipment failure
- On recognition, Orchestrator creates a `DisruptionEvent` and asks Planner to confirm before proceeding
- If Planner message is ambiguous, Orchestrator asks clarifying questions (never assumes)

## BR-OA-02: Sub-Agent Invocation Pattern

- All three sub-agents (Impact Assessment, Capacity & Optimization, Constraint Matching) are exposed as Strands `@tool` functions
- Each tool wraps an AgentCore managed runtime invocation — sub-agents run as separate AgentCore agents
- The Orchestrator LLM decides when to invoke each sub-agent based on conversation context and system prompt guidance
- Sub-agent tools accept a text prompt and return the sub-agent's text response
- The Orchestrator MUST NOT import sub-agent Python packages directly — all invocation goes through AgentCore API

## BR-OA-03: Round 1 Execution

- Round 1 invokes Impact Assessment Agent and Capacity & Optimization Agent
- Since sub-agents are Strands tools and the LLM drives invocation, Round 1 is sequential (LLM calls one tool, then the other)
- The system prompt instructs the LLM to invoke both agents before presenting Round 1 results
- Round 1 is complete when both agents have written their shared context (prioritized_orders + capacity_snapshot)
- Orchestrator presents a combined Round 1 summary to the Planner after both agents complete

## BR-OA-04: Round 2 Execution — Delay Phase

- After Round 1 summary, Orchestrator transitions to Round 2
- Round 2 Step 1: Orchestrator invokes Capacity & Optimization Agent for delay candidate identification
- Delay candidates are Ohio P3 orders with deadline > 6 weeks
- Each delay candidate is presented to Planner one at a time via the sub-agent
- Planner approves or rejects each delay — decisions are relayed back to the sub-agent
- After all delay decisions, Capacity & Optimization Agent recalculates and writes updated capacity_snapshot

## BR-OA-05: Round 2 Execution — Constraint Funnel Phase

- Round 2 Step 2: Orchestrator invokes Constraint Matching Agent for the 4-layer funnel
- Constraint Matching Agent processes Florida orders in priority order (P1 first)
- Each order recommendation is presented to Planner for approve/reject/skip
- Planner decisions are relayed back to the sub-agent
- Running capacity tracker is updated after each decision
- Round 2 is complete when all Florida orders have been processed or Planner ends early

## BR-OA-06: What-If Recalculation

- When Planner asks a what-if question, the Orchestrator LLM analyzes the question
- LLM determines which sub-agent(s) are affected based on the question content
- Orchestrator re-invokes only the affected agent(s) with the modified parameters
- If capacity changes, downstream constraint matching is automatically re-triggered
- What-if results are streamed back to Planner with a comparison to previous state
- Each what-if is logged as an audit entry

## BR-OA-07: Session State Management

- Orchestrator uses hybrid state management:
  - Strands Agent conversation history holds the full LLM context (messages, tool calls, results)
  - Explicit `WorkflowSession` dataclass tracks programmatic state (current phase, decisions, errors)
- Session state is updated after every significant event (phase transition, decision, error)
- Session state is written to AgentCore Memory for recovery on reconnection
- Session timeout: 60 minutes of inactivity — after timeout, session is marked COMPLETE

## BR-OA-08: Error Recovery

- If a sub-agent tool call fails, Orchestrator retries once with the same input
- If retry succeeds, workflow continues normally — failure is logged but not surfaced to Planner
- If retry fails:
  - Orchestrator continues with partial results where possible
  - Example: If Capacity Agent fails but Impact Agent succeeded in Round 1, present partial results
  - Orchestrator informs Planner: "Capacity analysis is unavailable. Proceeding with priority assessment only."
  - Failed agent is marked in session state — Planner can request manual retry later
- If a critical agent fails (no partial results possible), Orchestrator halts and explains to Planner

## BR-OA-09: Streaming Coordination

- Natural language tokens from sub-agents stream through the Orchestrator's Strands callback
- Structured data (tables, tracker updates, approval requests) is sent as complete JSON payloads
- Orchestrator adds agent identification to each stream (agent_name field)
- Phase transition messages are sent as `phase_update` payloads
- Orchestrator does NOT buffer or rewrite sub-agent natural language — pass-through for text

## BR-OA-10: Audit Trail

- Orchestrator writes audit entries for all workflow-level events via Audit MCP
- Sub-agents write their own domain-specific audit entries independently
- Orchestrator audit entries use action types defined in domain-entities.md
- If Audit MCP write fails, Orchestrator logs warning but does NOT halt workflow
- Audit entries include session_id for correlation across all agents

## BR-OA-11: Summary Generation

- After all Round 2 decisions are complete, Orchestrator generates a plain-language summary
- Summary includes: total orders processed, approvals/rejections/skips, capacity utilization, key decisions
- Summary is generated by the Orchestrator LLM (not a sub-agent) using conversation context
- Summary is written as a final audit entry with action "workflow_completed"

## BR-OA-12: Planner Interaction Rules

- Orchestrator NEVER makes decisions on behalf of the Planner
- All order approvals/rejections/skips require explicit Planner input
- Orchestrator presents recommendations with reasoning but waits for Planner confirmation
- If Planner asks to skip remaining orders, Orchestrator marks them as "skipped" and proceeds to summary
- If Planner asks to go back to a previous order, Orchestrator re-presents that order

## BR-OA-13: MCP Tool Access

- Orchestrator directly accesses Audit MCP for writing workflow-level audit entries
- Orchestrator does NOT directly access ERP Data MCP — all ERP data access is delegated to sub-agents
- MCP access uses `mcp-proxy-for-aws` with SigV4 auth to AgentCore Gateway
- MCP tool failures follow the same retry-once pattern as sub-agent failures

## BR-OA-14: Conversation Boundaries

- One workflow session = one disruption event
- Planner can start a new workflow by describing a new disruption event
- Previous session context is not carried into new sessions
- Within a session, full conversation history is maintained in the Strands Agent context window
- If context window approaches limit, Orchestrator summarizes older messages (Strands built-in)

## BR-OA-15: Input Validation

- All Planner messages are validated before processing (SECURITY-05)
- Maximum message length: 4000 characters
- Messages are sanitized for injection content before passing to LLM
- Empty or whitespace-only messages receive: "I didn't catch that. Could you rephrase?"
- Messages during an active sub-agent call are queued until the current operation completes
