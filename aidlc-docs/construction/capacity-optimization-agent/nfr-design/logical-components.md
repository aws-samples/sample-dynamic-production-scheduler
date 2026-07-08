# Logical Components — Unit 5: Capacity & Optimization Agent

## Component Overview

```
Orchestrator Agent
      |
      | invoke (Strands tool call)
      v
+-------------------------+
| Agent Entry Point       |  (fail-closed wrapper, Pattern 7)
+-------------------------+
      |
      v
+-------------------------+
| Strands Agent           |  (Claude 4.5 Haiku, system prompt)
+-------------------------+
      |
      +--------+----------+
      |                   |
      v                   v
+-----------+   +------------------+
| MCP Tools |   | Python Tools     |
| (HTTP/SSE)|   | (capacity calcs) |
+-----------+   +------------------+
      |                   |
      v                   v
+-------------------------+
| Capacity State Cache    |  (in-memory snapshot, Pattern 8)
+-------------------------+
      |
      v
+-------------------------+
| Logging Layer           |  (JSON structured, Pattern 4)
+-------------------------+
      |
      v
+-------------------------+
| AgentCore Runtime       |  (hosting, scaling, lifecycle)
+-------------------------+
```

---

## Component 1: Agent Entry Point

- **Module**: `agent.py`
- **Responsibility**: Initialize Strands Agent, configure model, register tools, expose invocation interface
- **Pattern**: Fail-Closed Agent Wrapper (Pattern 7)
- **Startup sequence**:
  1. Load AgentSettings from environment
  2. Validate business thresholds (window > 0, threshold > 0, warning in 0-1)
  3. Configure structured logging
  4. Initialize BedrockModel (Claude 4.5 Haiku, temp=0, timeout=30s)
  5. Register MCP tools (via AgentCore Gateway HTTP/SSE)
  6. Register Python tools (capacity calculations, delay processing, constraint handling)
  7. Create Agent instance with system prompt

## Component 2: Agent Configuration

- **Module**: `config.py`
- **Responsibility**: Load and validate all agent settings from environment
- **Pattern**: Environment-Based Configuration (Pattern 5)
- **Validates at startup**:
  - rerouting_window_days > 0
  - delay_threshold_days > 0
  - utilization_warning_pct between 0.0 and 1.0
  - Bedrock model ID is non-empty
  - MCP Gateway URL is non-empty
- **Fails fast**: If configuration invalid, agent exits with clear error

## Component 3: Capacity Engine

- **Module**: `capacity.py`
- **Responsibility**: Pure Python capacity calculations (surplus, bottleneck, delay, constraints)
- **Pattern**: Capacity Calculations as Pure Python (Pattern 3)
- **Functions**:
  - `compute_tiered_utilization(machine_capacity, committed_hours, window_days)` — per-machine surplus by shift tier
  - `compute_manpower_surplus(manpower_data, allocated)` — operator availability
  - `compute_material_surplus(materials, committed)` — raw material availability
  - `compute_order_slack(orders, daily_capacity)` — slack days per order
  - `identify_bottleneck(machine_surpluses, florida_demand)` — ratio-based (BR-CO-04)
  - `filter_delay_candidates(orders, threshold, customers)` — eligibility + sort (BR-CO-06, BR-CO-07)
  - `compute_freed_capacity(order)` — 4-dimension freed capacity (BR-CO-08)
  - `assess_delay_risk(slack_days, threshold)` — Low/Medium/High (BR-CO-09)
  - `apply_constraint(snapshot, constraint)` — global constraint application (BR-CO-11, BR-CO-12)
  - `process_delay_decision(state, order_id, action, freed)` — immediate recalculation (BR-CO-10)
  - `build_capacity_snapshot(...)` — assemble all 5 dimensions into CapacitySnapshot
- **Key property**: Deterministic — same input always produces same output
- **Registered as**: Strands Python tools (LLM calls them after fetching MCP data)

## Component 4: Capacity State Cache

- **Module**: `capacity.py` (CapacityState class)
- **Responsibility**: In-memory cache of current CapacitySnapshot for fast recalculations
- **Pattern**: Cached Snapshot for Recalculations (Pattern 8)
- **Behavior**:
  - Initialized after first capacity analysis completes
  - Delay decisions mutate cached snapshot (no MCP re-fetch)
  - Constraint applications mutate cached snapshot (no MCP re-fetch)
  - Updated snapshot persisted to AgentCore Memory after each mutation
  - Enables 10s response time for delay/constraint operations

## Component 5: Pydantic Schema Models

- **Module**: `models/schemas.py`
- **Responsibility**: Input/output validation for all agent data
- **Pattern**: Input Validation (Pattern 6)
- **Models**: CapacitySnapshot, EquipmentCapability, ShiftUtilization, ShiftTier, MachineUtilization, ManpowerAvailability, MaterialSurplus, OhioOrderLoad, BottleneckInfo, SurplusSummary, DelayCandidateInfo, DelayDecision, DelayResult, PlannerConstraint, ConstraintImpact, DelayDecisionInput, ConstraintInput, AgentSettings
- **Validates**: order_id format, constraint text length, action enum, threshold ranges

## Component 6: System Prompt

- **Module**: `prompts/system_prompt.py`
- **Responsibility**: Define agent persona, tool usage instructions, failure handling rules
- **Contents**:
  - Agent role: "You are the Capacity & Optimization Agent for DisruptionAI"
  - Available tools: MCP tools (get_machine_capacity, get_manpower, get_materials, get_orders, get_customers, write_audit_entry) + Python tools (compute_capacity_snapshot, filter_delay_candidates, process_delay_decision, apply_constraint)
  - Workflow: fetch data -> compute snapshot -> present tables -> handle delays/constraints
  - Failure handling rules (per BR-CO-15)
  - Presentation format (5 tables for capacity, candidate list for delays, before/after for constraints)

## Component 7: Structured Logger

- **Module**: `logging_config.py`
- **Responsibility**: JSON-formatted logging to stdout
- **Pattern**: Structured Agent Logging (Pattern 4)
- **Fields**: timestamp, level, agent_name, session_id, duration_ms, message
- **Destination**: stdout (captured by AgentCore runtime to CloudWatch)

---

## Tool Registration

The agent registers two categories of tools:

### MCP Tools (via AgentCore Gateway HTTP/SSE)
| Tool | MCP Server | Purpose |
|------|-----------|---------|
| get_machine_capacity | ERP Data MCP | Fetch Rolling Mill / Finishing Line data |
| get_manpower | ERP Data MCP | Fetch operator availability |
| get_materials | ERP Data MCP | Fetch raw material inventory |
| get_orders | ERP Data MCP | Fetch existing Ohio orders |
| get_customers | ERP Data MCP | Fetch customer penalty clause data |
| write_audit_entry | Audit MCP | Log decisions to audit trail |

### Python Tools (local, registered with Strands)
| Tool | Module | Purpose |
|------|--------|---------|
| compute_capacity_snapshot | capacity.py | Run full 5-dimension capacity analysis |
| filter_delay_candidates | capacity.py | Identify eligible delay candidates |
| process_delay_decision | capacity.py | Handle approve/reject + recalculate |
| apply_constraint | capacity.py | Apply planner constraint + recalculate |
| get_surplus_summary | capacity.py | Generate surplus summary text |

---

## Cross-Cutting Concerns

| Concern | Component | Pattern |
|---------|-----------|---------|
| LLM retry | Strands Agent | Exponential backoff (Pattern 1) |
| MCP failure handling | System Prompt | Tiered failure rules (Pattern 2) |
| Calculation performance | Capacity Engine | Pure Python (Pattern 3) |
| Logging | Structured Logger | JSON middleware (Pattern 4) |
| Configuration | Agent Configuration | Environment variables (Pattern 5) |
| Input validation | Pydantic Models | Schema enforcement (Pattern 6) |
| Fail-closed | Agent Entry Point | Global wrapper (Pattern 7) |
| Recalculation speed | Capacity State Cache | Cached snapshot (Pattern 8) |

---

## Data Flow

```
1. Orchestrator invokes agent("Analyze Ohio capacity")
      |
      v
2. LLM calls get_machine_capacity("Rolling Mill")
   LLM calls get_machine_capacity("Finishing Line")
   LLM calls get_manpower()
   LLM calls get_materials()
   LLM calls get_orders(plant="Ohio", status="Active")
   LLM calls get_customers()
      |  (HTTP/SSE to AgentCore Gateway -> ERP Data MCP)
      v
3. LLM calls compute_capacity_snapshot(all fetched data)
      |  (local Python tool -- deterministic, < 5ms)
      v
4. Agent writes CapacitySnapshot to AgentCore Memory
      |
      v
5. Agent presents 5 capacity tables + bottleneck summary
      |
      v
6. [If delay optimization requested]
   LLM calls filter_delay_candidates(orders, threshold)
      |  (local Python tool)
      v
7. Agent presents delay candidates to Planner
      |
      v
8. For each Planner decision:
   LLM calls process_delay_decision(order_id, action)
      |  (local Python tool -- recalculates from cache)
      v
   LLM calls write_audit_entry(decision details)
      |  (HTTP/SSE to AgentCore Gateway -> Audit MCP)
      v
   Agent presents updated surplus
      |
      v
9. [If constraint requested]
   LLM calls apply_constraint(constraint_text)
      |  (local Python tool -- recalculates from cache)
      v
   Agent presents before/after comparison
```
