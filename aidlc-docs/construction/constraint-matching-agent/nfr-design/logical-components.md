# Logical Components — Unit 6: Constraint Matching Agent

## Component Overview

```
Orchestrator Agent
      |
      | invoke (Strands tool call)
      v
+---------------------------+
| Agent Entry Point         |  (fail-closed wrapper, Pattern 7)
+---------------------------+
      |
      v
+---------------------------+
| Strands Agent             |  (Claude 4.5 Haiku, system prompt)
+---------------------------+
      |
      +--------+------------+
      |                     |
      v                     v
+-----------+   +---------------------+
| MCP Tools |   | Python Tools        |
| (HTTP/SSE)|   | (funnel + tracker)  |
+-----------+   +---------------------+
      |                     |
      v                     v
+---------------------------+
| Tracker State Singleton   |  (in-memory, Pattern 8)
+---------------------------+
      |
      v
+---------------------------+
| Logging Layer             |  (JSON structured, Pattern 4)
+---------------------------+
      |
      v
+---------------------------+
| AgentCore Runtime         |  (hosting, scaling, lifecycle)
+---------------------------+
```

---

## Component 1: Agent Entry Point

- **Module**: `agent.py`
- **Responsibility**: Initialize Strands Agent, configure model, register tools, expose invocation interface
- **Pattern**: Fail-Closed Agent Wrapper (Pattern 7)
- **Startup sequence**:
  1. Load AgentSettings from environment
  2. Validate business thresholds (warning pct in 0-1, cascade depth > 0, timeout > 0)
  3. Configure structured logging
  4. Initialize BedrockModel (Claude 4.5 Haiku, temp=0, timeout=20s)
  5. Register MCP tools (via AgentCore Gateway HTTP/SSE)
  6. Register Python tools (evaluate_funnel, simulate_cascade, tracker operations)
  7. Create Agent instance with system prompt

## Component 2: Agent Configuration

- **Module**: `config.py`
- **Responsibility**: Load and validate all agent settings from environment
- **Pattern**: Environment-Based Configuration (Pattern 5)
- **Validates at startup**:
  - utilization_warning_pct between 0.0 and 1.0
  - max_cascade_depth > 0
  - cascade_timeout_secs > 0
  - checkpoint_interval_secs > 0
  - Bedrock model ID is non-empty
  - MCP Gateway URL is non-empty
- **Fails fast**: If configuration invalid, agent exits with clear error

## Component 3: Constraint Funnel Engine

- **Module**: `funnel.py`
- **Responsibility**: Pure Python 4-layer constraint funnel (no LLM calls)
- **Pattern**: Constraint Funnel as Pure Python — Hybrid Tool Design (Pattern 3)
- **Functions**:
  - `evaluate_funnel(order, equipment, materials, manpower, ohio_orders, tracker, config)` — runs all 4 layers, returns FunnelResult
  - `check_equipment_compatibility(order, equipment)` — Layer 1: product family + gauge range
  - `check_material_availability(order, materials, tracker)` — Layer 2: surplus + procurement feasibility
  - `check_utilization_and_manpower(order, tracker, manpower, config)` — Layer 3: tiered shift + manpower
  - `simulate_cascade(florida_order, ohio_orders, config)` — Layer 4: multi-level cascade with timeout
  - `derive_recommendation(l1, l2, l3, l4)` — composite recommendation category
- **Key property**: Deterministic — same input + same tracker state = same output
- **Registered as**: Two Strands Python tools:
  - `evaluate_funnel` — primary tool, called per order
  - `simulate_cascade` — standalone, for on-demand re-simulation

## Component 4: Running Capacity Tracker

- **Module**: `tracker.py`
- **Responsibility**: Module-level singleton managing running capacity state
- **Pattern**: Running Capacity Tracker Singleton (Pattern 8)
- **Behavior**:
  - Initialized from shared context snapshot or loaded from DynamoDB
  - All funnel functions access singleton directly via `TrackerState.get()`
  - `approve_order()` — tiered hour consumption (normal -> OT -> weekend) + material + manpower deduction
  - `skip_order()` — add to skip list, no capacity change
  - `reject_order()` — add to reject list, no capacity change
  - Persisted to DynamoDB via `update_running_tracker` after every decision
  - Periodic checkpoint every 5 minutes (configurable)
  - Session-scoped via session_id — complete isolation between sessions

## Component 5: Pydantic Schema Models

- **Module**: `models/schemas.py`
- **Responsibility**: Input/output validation for all agent data
- **Pattern**: Input Validation (Pattern 6)
- **Models**: FunnelResult, EquipmentCheckResult, MaterialCheckResult, UtilizationCheckResult, ShiftEscalationOption, CascadeImpactResult, CascadeImpactedOrder, RunningCapacityTracker, RunningShiftHours, ProcessedOrderEntry, OrderDecision, OrderDecisionResult, CapacityConsumed, SkipQueueEntry, OrderDecisionInput, RevisitInput, AgentConfig, TransferSummary, ConstraintMatchingAuditEntry
- **Validates**: order_id format (PO-YYYY-NNN), decision action enum, gauge ranges, hour values >= 0

## Component 6: System Prompt

- **Module**: `prompts/system_prompt.py`
- **Responsibility**: Define agent persona, tool usage instructions, failure handling rules
- **Contents**:
  - Agent role: "You are the Constraint Matching Agent for DisruptionAI"
  - Available tools: MCP tools (get_machine_capacity, get_materials, get_orders, get_manpower, get_running_tracker, update_running_tracker, write_audit_entry) + Python tools (evaluate_funnel, simulate_cascade, approve_order, reject_order, skip_order)
  - Workflow: initialize data -> build priority queue -> for each order: evaluate_funnel -> present to Planner -> process decision -> update tracker
  - Failure handling rules (per BR-CM-13)
  - Presentation format (per-order funnel results with layer-by-layer breakdown)
  - Decision handling (approve/reject/skip/revisit)

## Component 7: Structured Logger

- **Module**: `logging_config.py`
- **Responsibility**: JSON-formatted logging to stdout
- **Pattern**: Structured Agent Logging (Pattern 4)
- **Fields**: timestamp, level, agent_name, session_id, order_id, duration_ms, message
- **Destination**: stdout (captured by AgentCore runtime to CloudWatch)

---

## Tool Registration

The agent registers two categories of tools:

### MCP Tools (via AgentCore Gateway HTTP/SSE)
| Tool                   | MCP Server    | Purpose                                    |
|------------------------|---------------|--------------------------------------------|
| get_machine_capacity   | ERP Data MCP  | Equipment capability for Layer 1           |
| get_materials          | ERP Data MCP  | Material inventory for Layer 2             |
| get_orders             | ERP Data MCP  | Ohio active orders for Layer 4 cascade     |
| get_manpower           | ERP Data MCP  | Manpower data for Layer 3                  |
| get_running_tracker    | ERP Data MCP  | Load persisted tracker (session resumption) |
| update_running_tracker | ERP Data MCP  | Persist tracker after each decision        |
| write_audit_entry      | Audit MCP     | Log funnel evaluations and decisions       |

### Python Tools (local, registered with Strands)
| Tool               | Module     | Purpose                                       |
|--------------------|------------|-----------------------------------------------|
| evaluate_funnel    | funnel.py  | Run all 4 constraint layers for an order      |
| simulate_cascade   | funnel.py  | Standalone cascade simulation (on-demand)     |
| approve_order      | tracker.py | Deduct capacity, update tracker, mark approved |
| reject_order       | tracker.py | Mark order non-transferable                   |
| skip_order         | tracker.py | Add to skip queue, no capacity change         |

---

## Cross-Cutting Concerns

| Concern                | Component              | Pattern                              |
|------------------------|------------------------|--------------------------------------|
| LLM retry              | Strands Agent          | Exponential backoff (Pattern 1)      |
| MCP failure handling   | System Prompt          | Tiered failure rules (Pattern 2)     |
| Funnel performance     | Funnel Engine          | Pure Python hybrid (Pattern 3)       |
| Logging                | Structured Logger      | JSON middleware (Pattern 4)          |
| Configuration          | Agent Configuration    | Environment variables (Pattern 5)    |
| Input validation       | Pydantic Models        | Schema enforcement (Pattern 6)       |
| Fail-closed            | Agent Entry Point      | Global wrapper (Pattern 7)           |
| Tracker state          | Tracker Singleton      | Module-level singleton (Pattern 8)   |
| Cascade timeout        | Funnel Engine          | Graceful degradation (Pattern 9)     |

---

## Data Flow

```
1. Orchestrator invokes agent("Match Florida orders to Ohio capacity")
      |
      v
2. LLM calls get_machine_capacity("Rolling Mill")
   LLM calls get_machine_capacity("Finishing Line")
   LLM calls get_materials()
   LLM calls get_orders(plant="Ohio", status="Active")
   LLM calls get_manpower()
   LLM calls get_running_tracker(session_id)
      |  (HTTP/SSE to AgentCore Gateway -> ERP Data MCP)
      v
3. Initialize TrackerState singleton from snapshot or DynamoDB
      |
      v
4. Build priority queue (P1 desc score, P2, P3)
      |
      v
5. For each order in queue:
   LLM calls evaluate_funnel(order, equipment, materials,
                             manpower, ohio_orders, tracker, config)
      |  (local Python tool -- deterministic, < 10ms)
      v
6. Agent presents funnel results + recommendation to Planner
      |
      v
7. Planner decides: approve / reject / skip
      |
      v
8a. [If approve]:
    LLM calls approve_order(order_id, rm_hrs, fl_hrs, tons, manpower)
       |  (local Python tool -- updates singleton)
       v
    LLM calls update_running_tracker(tracker)
       |  (HTTP/SSE to AgentCore Gateway -> ERP Data MCP)
       v
    LLM calls write_audit_entry(decision details)
       |  (HTTP/SSE to AgentCore Gateway -> Audit MCP)
       v
    Agent presents updated capacity summary
      |
      v
8b. [If reject]:
    LLM calls reject_order(order_id)
    LLM calls update_running_tracker(tracker)
    LLM calls write_audit_entry(rejection)
      |
      v
8c. [If skip]:
    LLM calls skip_order(order_id)
    LLM calls update_running_tracker(tracker)
    LLM calls write_audit_entry(skip)
    Order appended to end of queue
      |
      v
9. [If revisit requested]:
   LLM calls evaluate_funnel(order) with current tracker state
   Present updated results
      |
      v
10. [End of queue]:
    Present transfer summary (approved/rejected/skipped counts)
    Write final audit entry
    Return control to Orchestrator
```
