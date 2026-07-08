# Domain Entities — Unit 7: Orchestrator Agent

## Overview

The Orchestrator Agent is the top-level coordinator for the DisruptionAI workflow. It manages conversation state, invokes sub-agents (Units 4, 5, 6) as Strands tools backed by AgentCore managed runtime, relays streaming output, and coordinates the two-round disruption response workflow. It does not own business logic — it delegates to specialist agents and synthesizes results.

---

## Agent Configuration Schema

```python
@dataclass
class OrchestratorConfig:
    model_id: str                # "us.anthropic.claude-4-5-haiku-20250514-v1:0"
    max_turns: int               # default 100 — max LLM turns per session
    retry_limit: int             # default 1 — retries per sub-agent call
    session_timeout_minutes: int # default 60
    sub_agents: SubAgentEndpoints

@dataclass
class SubAgentEndpoints:
    impact_assessment_agent_id: str    # AgentCore agent ID for Unit 4
    capacity_optimization_agent_id: str # AgentCore agent ID for Unit 5
    constraint_matching_agent_id: str   # AgentCore agent ID for Unit 6

@dataclass
class MCPServerEndpoints:
    audit_mcp_url: str          # AgentCore Gateway URL for Audit MCP
    erp_data_mcp_url: str       # AgentCore Gateway URL for ERP Data MCP
```

---

## Session State Entity

```python
@dataclass
class WorkflowSession:
    session_id: str
    created_at: str              # ISO timestamp
    current_phase: WorkflowPhase
    disruption_event: DisruptionEvent | None
    round1_complete: bool
    round2_complete: bool
    decisions: list[OrderDecision]
    what_if_count: int           # number of what-if recalculations performed
    error_log: list[AgentError]

class WorkflowPhase(str, Enum):
    IDLE = "idle"
    DISRUPTION_DETECTED = "disruption_detected"
    ROUND1_IN_PROGRESS = "round1_in_progress"
    ROUND1_COMPLETE = "round1_complete"
    ROUND2_DELAYS = "round2_delays"
    ROUND2_FUNNEL = "round2_funnel"
    WHAT_IF = "what_if"
    SUMMARY = "summary"
    COMPLETE = "complete"
```

---

## Disruption Event Entity

```python
@dataclass
class DisruptionEvent:
    event_type: str              # "tornado", "hurricane", "flood", etc.
    affected_plant: str          # "Florida"
    description: str             # Planner's description of the event
    detected_at: str             # ISO timestamp
    severity: str | None         # optional — "severe", "moderate", "minor"
```

---

## Sub-Agent Invocation Entities

```python
@dataclass
class SubAgentRequest:
    agent_id: str                # AgentCore agent ID
    input_text: str              # prompt/instruction sent to sub-agent
    session_id: str              # workflow session for context scoping

@dataclass
class SubAgentResponse:
    agent_id: str
    output_text: str             # full text response from sub-agent
    success: bool
    error_message: str | None
    duration_ms: int
```

---

## Order Decision Entity

Tracks each Planner decision made during the workflow.

```python
@dataclass
class OrderDecision:
    order_id: str
    decision_type: str           # "delay_approval" | "delay_rejection" | "reroute_approve" | "reroute_reject" | "reroute_skip"
    agent_source: str            # "capacity_optimization" | "constraint_matching"
    round: int                   # 1 or 2
    timestamp: str               # ISO timestamp
    details: dict                # agent-specific context (freed capacity, funnel results, etc.)
```

---

## Agent Error Entity

```python
@dataclass
class AgentError:
    agent_id: str
    error_type: str              # "timeout" | "exception" | "invalid_response"
    message: str
    timestamp: str
    retried: bool
    retry_succeeded: bool | None
```

---

## Streaming Entities

```python
@dataclass
class StreamToken:
    token: str
    agent_name: str              # which sub-agent produced this token
    token_type: str              # "text" | "structured_data"

@dataclass
class StructuredPayload:
    payload_type: str            # "table" | "tracker" | "summary" | "approval_request"
    data: dict                   # JSON-serializable payload
    agent_name: str
```

---

## Audit Entry Schema (Orchestrator-specific)

```python
@dataclass
class OrchestratorAuditEntry:
    session_id: str
    agent: str                   # "orchestrator_agent"
    action: str                  # see action types below
    timestamp: str               # ISO timestamp
    details: dict
```

### Action Types

| Action | When | Details |
|--------|------|---------|
| `workflow_started` | Disruption confirmed | `{event_type, affected_plant, description}` |
| `round1_started` | Round 1 begins | `{agents_invoked: ["impact_assessment", "capacity_optimization"]}` |
| `round1_completed` | Round 1 ends | `{duration_ms, agents_succeeded, agents_failed}` |
| `round2_started` | Round 2 begins | `{phase: "delays" or "funnel"}` |
| `round2_completed` | Round 2 ends | `{total_decisions, approvals, rejections, skips}` |
| `what_if_requested` | Planner asks what-if | `{question, agents_reinvoked}` |
| `what_if_completed` | What-if resolved | `{duration_ms, changes_summary}` |
| `workflow_completed` | Summary generated | `{total_orders_processed, total_decisions, duration_ms}` |
| `agent_error` | Sub-agent failure | `{agent_id, error_type, retried, recovered}` |

---

## Shared Context Keys (AgentCore Memory)

The Orchestrator reads and coordinates these shared context keys:

| Key | Written By | Read By | Content |
|-----|-----------|---------|---------|
| `prioritized_orders` | Impact Assessment Agent | Capacity & Optimization, Constraint Matching | Scored Florida orders with P1/P2/P3 |
| `capacity_snapshot` | Capacity & Optimization Agent | Constraint Matching Agent | Ohio plant capacity across 5 dimensions |
| `workflow_session` | Orchestrator Agent | All agents | Current session state and phase |

---

## Entity Relationships

```
OrchestratorConfig
  +-- SubAgentEndpoints (3 AgentCore agent IDs)
  +-- MCPServerEndpoints (Audit MCP, ERP Data MCP)

WorkflowSession
  +-- WorkflowPhase (enum — current state)
  +-- DisruptionEvent (trigger)
  +-- OrderDecision[] (all Planner decisions)
  +-- AgentError[] (failure log)

SubAgentRequest --> SubAgentResponse (1:1 per invocation)

StreamToken / StructuredPayload --> WebSocket relay to frontend

OrchestratorAuditEntry --> Audit MCP (write_audit_entry)
```
