# Requirements Document — DisruptionAI

## Intent Analysis Summary

- **User Request**: Build Agentic-AI powered dynamic production scheduling system ("DisruptionAI") as specified in the Builder Spec
- **Request Type**: New Feature / New Project (Greenfield)
- **Scope Estimate**: Multi-component system (4-agent backend, React frontend, DynamoDB data layer, WebSocket API)
- **Complexity Estimate**: Complex — multi-agent orchestration, multi-constraint AI reasoning, real-time streaming, AWS infrastructure

---

## Project Overview

**DisruptionAI** is a Multi-Agent AI system that helps Production Planners rapidly respond to catastrophic manufacturing disruptions. When a plant goes offline (e.g., tornado shuts down Florida plant), the AI agents collaborate with the Planner to:

1. Assess impact and prioritize affected production orders
2. Analyze capacity at alternate plants (Ohio)
3. Reallocate production through a 4-layer constraint matching engine
4. Keep the human in control at every decision point

**Business Context**: ABC Steel Corporation — Steel Manufacturing with two plants (Columbus OH, Florida).

---

## Multi-Agent Architecture

### Agent Overview

DisruptionAI uses a 4-agent architecture coordinated by an Orchestrator:

| Agent | Responsibility | Phase Mapping |
|-------|---------------|---------------|
| **Orchestrator Agent** | Coordinates workflow, manages Planner conversation, handles what-if re-planning, maintains audit trail | All phases |
| **Impact Assessment Agent** | Evaluates and prioritizes Florida orders by urgency, customer tier, and value | Phase 1 |
| **Capacity & Optimization Agent** | Assesses Ohio plant capacity across all 5 dimensions (equipment, utilization, manpower, material, existing load); identifies delay candidates and frees capacity | Phase 2 & Phase 3 Step 1-2 |
| **Constraint Matching Agent** | Runs 4-layer constraint matching, assigns orders to Ohio slots, interactive order-by-order flow | Phase 3 Step 3 |

### Execution Flow

```
Round 1 (Parallel):
+-----------------------------+     +-------------------------------+
| Impact Assessment Agent     |     | Capacity & Optimization Agent |
| - Query Florida orders      |     | - Equipment capability        |
| - Apply priority algo       |     | - Machine utilization         |
| - Output: P1/P2/P3 tags    |     | - Manpower headcount          |
+-----------------------------+     | - Raw material surplus        |
            |                       | - Existing Ohio load          |
            |                       +-------------------------------+
            |                                   |
            v                                   v
+---------------------------------------------------------------+
|                       Shared Context                          |
| - Prioritized Florida orders (P1, P2, P3)                     |
| - Ohio capacity snapshot (all 5 dimensions)                   |
+---------------------------------------------------------------+
                                |
                                v
Round 2 (Sequential, Interactive):
+---------------------------------------------------------------+
|              Capacity & Optimization Agent                    |
| - Identify Ohio delay candidates                              |
| - Calculate freed capacity per candidate                      |
| - Interactive: Planner approves/rejects each delay            |
| - Recalculate post-delay capacity                             |
+---------------------------------------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|                Constraint Matching Agent                      |
| - Process orders by priority (P1 first)                       |
| - 4-layer constraint funnel per order                         |
| - Interactive: present order -> Planner approves/rejects      |
| - Update running capacity tracker after each decision         |
+---------------------------------------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|                    Orchestrator Agent                         |
| - Coordinate Round 1 parallel execution                       |
| - Sequence Round 2 interactive flow                           |
| - Handle what-if recalculations                               |
| - Generate plain-language summaries                           |
| - Write decisions to audit log                                |
+---------------------------------------------------------------+
```

### Agent Communication Pattern

- **Round 1**: Orchestrator fires Impact Assessment Agent and Capacity & Optimization Agent in parallel
- **Shared Context**: Both agents write to a shared context (in-memory state or DynamoDB)
- **Round 2**: Capacity & Optimization Agent handles delay candidates first, then Constraint Matching Agent reads shared context and processes orders interactively with Planner
- **What-If**: Orchestrator intercepts what-if questions, triggers re-execution of affected agents

---

## MVP Scope Definition

**In Scope (MVP)**:
- Phase 0: Disruption Detection & Alert (Orchestrator Agent)
- Phase 1: Impact Assessment & Prioritization (Impact Assessment Agent)
- Phase 2: Ohio Capacity Analysis (Capacity & Optimization Agent)
- Phase 3 Step 1: Free Up Capacity at Ohio Plant (Capacity & Optimization Agent)
- Phase 3 Step 2: Recalculate Ohio Capacity Post-Delay (Capacity & Optimization Agent)
- Phase 3 Step 3: Multi-Constraint Matching Engine (Constraint Matching Agent)

**Out of Scope (Deferred)**:
- Phase 3 Step 4: Non-Transferable Orders & Customer Communications
- Phase 4: Execution (order creation, schedule updates, notifications)
- AWS Cognito Authentication (deferred to post-MVP)

---

## Functional Requirements

### FR-01: Disruption Detection & Alert (Phase 0 — Orchestrator Agent)
- **FR-01.1**: Orchestrator detects disruption event (mock weather API for tornado)
- **FR-01.2**: Orchestrator correlates event with plant location (Florida)
- **FR-01.3**: Orchestrator sends proactive alert with at-risk order count
- **FR-01.4**: Planner confirms to trigger workflow

### FR-02: Order Prioritization (Phase 1 — Impact Assessment Agent)
- **FR-02.1**: Query Florida plant's open production orders (all orders from orders.json)
- **FR-02.2**: Apply weighted priority algorithm based on:
  - Days-to-due-date (urgency)
  - Customer tier (Tier1 / Tier2 / Tier3)
  - Order value (dollar amount)
  - Machine types required
- **FR-02.3**: Assign priority classification:
  - **P1 (Must Move)**: Critical orders requiring immediate rerouting
  - **P2 (Move if Capacity Allows)**: Important orders to transfer if resources permit
  - **P3 (Defer with Customer Notification)**: Lower-priority orders that can be delayed
- **FR-02.4**: Output priority distribution summary (e.g., "8 P1 orders, 7 P2 orders, 5 P3 orders")
- **FR-02.5**: Agent explains classification logic in natural language
- **FR-02.6**: Planner can reclassify orders; agent acknowledges and carries forward

### FR-03: Ohio Capacity Analysis (Phase 2 — Capacity & Optimization Agent)
- **FR-03.1**: Query Ohio equipment capability:
  - Rolling Mill: gauge range (min/max), available hours per shift type
  - Finishing Line: product family compatibility, available hours per shift type
- **FR-03.2**: Query machine utilization across shift types (Normal, Overtime, Weekend)
- **FR-03.3**: Account for setup time differences between product families
- **FR-03.4**: Query manpower headcount and availability
- **FR-03.5**: Query raw material inventory and surplus:
  - Current inventory by material type
  - Committed to existing Ohio orders
  - Available surplus
  - Procurement lead time
- **FR-03.6**: Query existing Ohio order load with slack calculations
- **FR-03.7**: Calculate total surplus capacity across 10-day rerouting window
- **FR-03.8**: Identify primary bottleneck (Rolling Mill vs Finishing Line)
- **FR-03.9**: Agent communicates bottleneck in natural language
- **FR-03.10**: Handle Planner-added constraints (e.g., "No weekend shifts") with immediate recalculation

### FR-04: Free Up Capacity (Phase 3 Step 1 — Capacity & Optimization Agent)
- **FR-04.1**: Query Ohio orders with P3 priority and deadline > 6 weeks
- **FR-04.2**: Calculate capacity freed per delay candidate:
  - Rolling Mill hours
  - Finishing Line hours
  - Raw material released (tons)
  - Operator hours freed
- **FR-04.3**: Calculate remaining buffer after delay
- **FR-04.4**: Agent explains trade-off per candidate with reasoning
- **FR-04.5**: Planner approves/rejects each delay
- **FR-04.6**: Agent recalculates surplus when Planner rejects without restarting

### FR-05: Recalculate Capacity (Phase 3 Step 2 — Capacity & Optimization Agent)
- **FR-05.1**: Re-run capacity calculation with approved delays removed
- **FR-05.2**: Show before/after comparison with clear delta
- **FR-05.3**: Identify updated bottleneck

### FR-06: Multi-Constraint Matching Engine (Phase 3 Step 3 — Constraint Matching Agent)
- **FR-06.1**: Process Florida orders through 4-layer constraint funnel (P1 first, then P2, then P3)
- **FR-06.2**: Layer 1 — Equipment Compatibility:
  - Check if Rolling Mill can handle required product family
  - Check if Finishing Line can handle required product family
- **FR-06.3**: Layer 2 — Raw Material Availability:
  - Full Match: Surplus inventory >= required quantity
  - Partial Match: Surplus < required, but procurement lead time + production time <= deadline
  - No Match: Insufficient and procurement exceeds deadline
- **FR-06.4**: Layer 3 — Machine Utilization:
  - Check available hours on both Rolling Mill AND Finishing Line
  - Running capacity tracker updates after each order
  - 90% threshold alerts
  - Shift type escalation (Normal → Overtime → Weekend)
  - Manpower headcount check
- **FR-06.5**: Layer 4 — Cascade Impact:
  - Simulate updated schedule after adding Florida order
  - Check if any existing Ohio order's slack goes negative (completion pushed past deadline)
  - Flag specific Ohio orders and penalty risk
- **FR-06.6**: Interactive conversation: Agent presents one order at a time (priority order), shows all 4 layers, recommends action
- **FR-06.7**: Planner approves/skips/rejects; agent updates running state
- **FR-06.8**: Handle Planner skip/reorder requests
- **FR-06.9**: Full what-if support: Orchestrator triggers re-execution of affected agents with modified parameters

### FR-07: Conversational UI
- **FR-07.1**: Chat interface for agent conversation
- **FR-07.2**: Side panel with structured approval form (Approve/Reject/Skip buttons)
- **FR-07.3**: Display structured data (tables, running capacity tracker) inline in chat
- **FR-07.4**: Streaming responses (tokens appear as agent thinks)
- **FR-07.5**: "Explain reasoning" expandable sections for each recommendation
- **FR-07.6**: Visual indication of which agent is currently active

### FR-08: Audit Trail (Orchestrator Agent)
- **FR-08.1**: Log every decision (human or AI) with timestamp and rationale
- **FR-08.2**: Log which agent made each recommendation
- **FR-08.3**: Persist audit trail to separate storage (survives restarts)
- **FR-08.4**: Display audit trail in UI for review

---

## Non-Functional Requirements

### NFR-01: Performance
- **NFR-01.1**: Agent response initiation < 2 seconds (first token)
- **NFR-01.2**: Round 1 parallel execution < 5 seconds total
- **NFR-01.3**: Constraint matching calculation < 5 seconds per order
- **NFR-01.4**: UI renders streaming tokens with < 100ms latency

### NFR-02: Scalability
- **NFR-02.1**: Support 20+ Florida production orders in mock data
- **NFR-02.2**: Support 20+ Ohio production orders in mock data
- **NFR-02.3**: ECS/Fargate auto-scaling for backend

### NFR-03: Availability
- **NFR-03.1**: Demo-grade availability (no HA requirements for MVP)

### NFR-04: Security
- **NFR-04.1**: SECURITY extension rules enforced (see Extension Configuration)
- **NFR-04.2**: No authentication for MVP (deferred)
- **NFR-04.3**: HTTPS for all communications
- **NFR-04.4**: Agent-to-agent communication secured within VPC

### NFR-05: Usability
- **NFR-05.1**: Single-user demo workflow
- **NFR-05.2**: Clear visual distinction between agent reasoning and recommendations
- **NFR-05.3**: Inline approval mechanism via side panel
- **NFR-05.4**: Clear indication of multi-agent coordination status

---

## Technical Architecture Decisions

### Compute
- **Backend**: AWS ECS/Fargate (Python)
- **Frontend**: Vite + React SPA (static hosting)

### Data Storage
- **Mock ERP Data**: AWS DynamoDB
- **Shared Agent Context**: DynamoDB or in-memory (agent state)
- **Audit Trail**: Separate storage (S3 or CloudWatch Logs)

### AI/Agent Framework
- **LLM Provider**: Amazon Bedrock (Claude via Strands Agents SDK)
- **Agent Pattern**: 4 specialized agents coordinated by Orchestrator
- **Tool Pattern**: Python functions registered as tools with Strands SDK

### API & Streaming
- **Streaming**: AWS API Gateway WebSocket API → ECS backend
- **Protocol**: WebSocket for bidirectional streaming

### Authentication
- **MVP**: No authentication
- **Post-MVP**: AWS Cognito (deferred)

---

## Data Model Summary

### Production Orders (Florida & Ohio)
| Field | Type | Description |
|-------|------|-------------|
| order_id | String | Unique production order ID (e.g., PO-2026-001) |
| plant | String | "Florida" or "Ohio" |
| product_family | String | Steel Sheets / Steel Coils / Steel Plates / Steel Bars |
| quantity | Number | Quantity in units |
| due_date | Date | Customer-committed deadline |
| machine_types_required | Array | ["Rolling Mill", "Finishing Line"] |
| customer_id | String | Customer identifier (e.g., CUST-1001) |
| order_value | Number | Dollar amount |
| customer_tier | String | Tier1 / Tier2 / Tier3 |
| priority | String | P1 / P2 / P3 (assigned by Impact Assessment Agent) |
| status | String | Active / Delayed / Transferred / Cancelled |
| rolling_mill_hours | Number | Estimated Rolling Mill hours (calculated) |
| finishing_line_hours | Number | Estimated Finishing Line hours (calculated) |

### Ohio Plant Capacity — Machines
| Field | Type | Description |
|-------|------|-------------|
| machine_type | String | Rolling Mill / Finishing Line |
| product_families_supported | Array | Product families this machine can process |
| planned_downtime_hrs_week | Number | Scheduled maintenance hours/week |
| utilization_pct_normal | Number | Current utilization % normal shifts |
| availability_pct_overtime | Number | Availability % overtime shifts |
| availability_pct_weekend | Number | Availability % weekend shifts |
| total_available_hrs_week | Number | Total available hours/week |
| setup_time_by_family | Object | Setup time in hours per product family transition |

### Ohio Plant Capacity — Manpower
| Field | Type | Description |
|-------|------|-------------|
| total_operators | Number | Total headcount |
| currently_allocated | Number | Operators on active Ohio orders |
| available_surplus | Number | Total minus Allocated |
| overtime_hrs_per_shift | Number | Available overtime hours/shift |
| weekend_hrs_per_shift | Number | Available weekend hours/shift |

### Ohio Plant Capacity — Raw Material
| Field | Type | Description |
|-------|------|-------------|
| material_type | String | Material identifier |
| current_inventory_tons | Number | Total inventory |
| committed_to_orders_tons | Number | Allocated to active Ohio orders |
| available_surplus_tons | Number | Current minus Committed |
| procurement_lead_time_days | Number | Days to procure additional stock |

### Customers
| Field | Type | Description |
|-------|------|-------------|
| customer_id | String | Unique customer ID |
| customer_name | String | Customer name |
| customer_tier | String | Tier1 / Tier2 / Tier3 |

---

## Priority Algorithm (Impact Assessment Agent)

The Impact Assessment Agent assigns priority using a weighted multi-criteria algorithm:

**Input Criteria:**
1. **Days-to-due-date**: Urgency based on deadline proximity
2. **Customer Tier**: Tier1 (highest) > Tier2 > Tier3 (lowest)
3. **Order Value**: Dollar amount of the order
4. **Machine Types Required**: Complexity of production requirements

**Output Classification:**
- **P1 (Must Move)**: Critical orders requiring immediate rerouting
- **P2 (Move if Capacity Allows)**: Important orders to transfer if resources permit
- **P3 (Defer with Customer Notification)**: Lower-priority orders that can be delayed

**Algorithm Details**: (To be refined during implementation)
- Weighted scoring model combining all 4 criteria
- Threshold-based classification into P1/P2/P3
- Configurable weights for different business scenarios

---

## Acceptance Criteria

### AC-01: Disruption Alert
- Given a tornado event approaching Florida
- When the Orchestrator detects the event
- Then the Orchestrator proactively alerts the Planner with at-risk order count

### AC-02: Priority Classification
- Given Florida orders with varying due dates, customer tiers, and values
- When the Impact Assessment Agent classifies orders
- Then orders are assigned P1/P2/P3 based on weighted criteria
- And the agent outputs a priority distribution summary

### AC-03: Parallel Agent Execution
- Given the Planner confirms the disruption alert
- When Round 1 begins
- Then Impact Assessment Agent and Capacity & Optimization Agent execute in parallel
- And both complete within 5 seconds

### AC-04: Capacity Bottleneck Identification
- Given Ohio plant capacity data
- When the Capacity & Optimization Agent analyzes capacity
- Then the agent identifies the primary bottleneck (Rolling Mill vs Finishing Line)
- And explains in natural language

### AC-05: 4-Layer Constraint Matching
- Given a Florida order to transfer
- When the Constraint Matching Agent evaluates the order
- Then all 4 layers are checked (Equipment, Material, Utilization, Cascade)
- And the agent shows pass/fail for each layer with reasoning

### AC-06: Cascade Impact Detection
- Given a transfer that would push an Ohio order past its deadline
- When the Constraint Matching Agent evaluates cascade impact
- Then the agent flags the specific Ohio order and impact

### AC-07: What-If Recalculation
- Given the Planner asks "What if I add weekend shifts?"
- When the Orchestrator processes the what-if
- Then affected agents re-execute with modified parameters
- And the Scheduler shows updated recommendations

### AC-08: Streaming Responses
- Given an agent is reasoning through a complex decision
- When the agent generates a response
- Then tokens stream to the UI in real-time

### AC-09: Agent Attribution
- Given multiple agents contribute to the workflow
- When decisions are logged to the audit trail
- Then each entry identifies which agent made the recommendation

---

## Extension Configuration

| Extension | Enabled | Decided At |
|-----------|---------|------------|
| Security Baseline | Yes | Requirements Analysis |

---

## Traceability Matrix

| Requirement | Builder Spec Section | Agent Responsible |
|-------------|---------------------|-------------------|
| FR-01 | Phase 0 | Orchestrator Agent |
| FR-02 | Phase 1 | Impact Assessment Agent |
| FR-03 | Phase 2 | Capacity & Optimization Agent |
| FR-04 | Phase 3 Step 1 | Capacity & Optimization Agent |
| FR-05 | Phase 3 Step 2 | Capacity & Optimization Agent |
| FR-06 | Phase 3 Step 3 | Constraint Matching Agent |
| FR-07 | Work Package 9 | Frontend (all agents) |
| FR-08 | Human-AI Collaboration | Orchestrator Agent |

---

## Constraints and Assumptions

### Constraints
- MVP scope limited to Phase 0 through Phase 3 Step 3
- No authentication for MVP
- Single-user demo (no concurrent users)
- Mock data only (no real ERP integration)
- 4-agent architecture (Orchestrator, Impact Assessment, Capacity & Optimization, Constraint Matching)

### Assumptions
- Strands Agents SDK supports multi-agent orchestration patterns
- Strands Agents SDK supports streaming via WebSocket
- DynamoDB single-digit millisecond latency sufficient for shared agent context
- Mock data includes 20 Florida orders and 20 Ohio orders with edge cases:
  - At least 1 equipment incompatibility (product family not supported)
  - At least 2 partial raw material matches
  - At least 1 cascade impact scenario
