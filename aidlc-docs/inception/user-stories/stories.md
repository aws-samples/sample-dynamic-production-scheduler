# User Stories — DisruptionAI

## Story Organization
- **Approach**: Hybrid — Phase-based primary grouping with agent attribution
- **Granularity**: Medium — 10 stories covering major agent interactions
- **Acceptance Criteria**: Detailed — 4-6 criteria per story
- **Persona**: Mr. John, Production Planner

---

## Phase 0: Disruption Detection & Alert

### US-01: Receive Proactive Disruption Alert
**As** Mr. John (Production Planner),
**I want** the system to proactively detect a catastrophic event threatening a plant and alert me with an impact summary,
**So that** I can begin the reallocation process immediately without waiting for manual reports.

**Agent**: Orchestrator Agent

**Acceptance Criteria**:
1. Orchestrator detects tornado event via mock weather API and correlates with Florida plant
2. Alert displays: event type, affected plant, estimated shutdown duration, count of at-risk orders
3. Alert includes a confirmation prompt: "Shall I begin impact assessment?"
4. Planner can confirm to trigger the workflow or dismiss the alert
5. Agent initiates without being asked — proactive, not reactive

**Traces to**: FR-01

---

## Phase 1: Impact Assessment

### US-02: View Prioritized Florida Orders
**As** Mr. John,
**I want** the Impact Assessment Agent to evaluate all Florida open orders and assign P1/P2/P3 priority tags with clear reasoning,
**So that** I know which orders are most critical and can focus reallocation efforts accordingly.

**Agent**: Impact Assessment Agent

**Acceptance Criteria**:
1. Agent queries all Florida open orders and applies weighted priority algorithm (days-to-due-date, customer tier, order value, machine types)
2. Each order is classified as P1 (Must Move), P2 (Move if Capacity Allows), or P3 (Defer with Customer Notification)
3. Agent displays a structured table with: order ID, product family, customer, priority, due date, quantity, order value
4. Agent provides a priority distribution summary (e.g., "8 P1, 7 P2, 5 P3")
5. Agent explains its classification logic in natural language for each priority level
6. Agent identifies which agent performed this assessment (Impact Assessment Agent attribution)

**Traces to**: FR-02

### US-03: Reclassify Order Priority
**As** Mr. John,
**I want** to override the AI's priority classification for any order and have the system carry my changes forward,
**So that** I maintain control over business-critical decisions the AI may not fully understand.

**Agent**: Impact Assessment Agent (via Orchestrator)

**Acceptance Criteria**:
1. Planner can select any order and change its priority (e.g., P2 to P1)
2. Agent acknowledges the reclassification with reasoning: "Understood. Order #X moved from P2 to P1."
3. Reclassified priority is carried forward into Phase 3 constraint matching
4. Audit trail logs the reclassification with timestamp, original priority, new priority, and who made the change

**Traces to**: FR-02.5, FR-02.6

---

## Phase 2: Ohio Capacity Analysis

### US-04: Review Ohio Plant Capacity Snapshot
**As** Mr. John,
**I want** the Capacity & Optimization Agent to assess Ohio's capacity across all dimensions and identify the primary bottleneck,
**So that** I understand what Ohio can absorb before we start matching orders.

**Agent**: Capacity & Optimization Agent

**Acceptance Criteria**:
1. Agent runs in parallel with Impact Assessment Agent (Round 1)
2. Agent reports capacity across 5 dimensions: equipment capability, machine utilization by shift type, manpower, raw material surplus, existing order load
3. Agent identifies and communicates the primary bottleneck in natural language (e.g., "Rolling Mill is the constraint at 45 surplus hours vs 140 on Finishing Line")
4. Capacity data is displayed as structured tables inline in the chat
5. Agent shows total available surplus capacity across the 10-day rerouting window

**Traces to**: FR-03

### US-05: Add Planner Constraints to Capacity
**As** Mr. John,
**I want** to add constraints (e.g., "No weekend shifts") and have the Capacity & Optimization Agent immediately recalculate,
**So that** the capacity analysis reflects real-world limitations the AI doesn't know about.

**Agent**: Capacity & Optimization Agent (via Orchestrator)

**Acceptance Criteria**:
1. Planner can state constraints in natural language (e.g., "No weekend shifts — union rules")
2. Capacity & Optimization Agent recalculates immediately with the new constraint applied
3. Agent shows before/after comparison of capacity impact
4. Updated bottleneck identification reflects the new constraint
5. What-if: Planner can ask "What if I authorize weekend shifts for 3 weeks?" and agent recalculates with that scenario

**Traces to**: FR-03.10

---

## Phase 3 Steps 1-2: Free Up Capacity

### US-06: Review and Approve Ohio Order Delays
**As** Mr. John,
**I want** the Capacity & Optimization Agent to identify Ohio orders that can be delayed to free capacity, with trade-off reasoning for each,
**So that** I can make informed decisions about which Ohio orders to delay.

**Agent**: Capacity & Optimization Agent

**Acceptance Criteria**:
1. Agent identifies Ohio orders with P3 priority and deadline > 6 weeks as delay candidates
2. For each candidate, agent shows: capacity freed (Rolling Mill hours, Finishing Line hours, material tons, operator hours), remaining buffer after delay
3. Agent explains trade-off reasoning per candidate (e.g., "Order #2015 frees 30 Rolling Mill hours. 2-week buffer remains. Low risk.")
4. Planner approves or rejects each delay individually
5. When Planner rejects a delay, agent recalculates surplus immediately and communicates downstream impact without restarting
6. After all delay decisions, agent shows before/after capacity comparison with updated bottleneck

**Traces to**: FR-04, FR-05

---

## Phase 3 Step 3: Multi-Constraint Matching

### US-07: Evaluate Orders Through 4-Layer Constraint Funnel
**As** Mr. John,
**I want** the Constraint Matching Agent to evaluate each Florida order through all 4 constraint layers and present results one order at a time,
**So that** I can understand exactly why each order can or cannot be transferred.

**Agent**: Constraint Matching Agent

**Acceptance Criteria**:
1. Agent processes orders in priority order (P1 first, then P2, then P3)
2. For each order, agent shows pass/fail for all 4 layers with reasoning:
   - Layer 1 (Equipment): Can Ohio machines handle this product family?
   - Layer 2 (Material): Full Match / Partial Match / No Match with lead time calculation
   - Layer 3 (Utilization): Available hours on both machines, threshold alerts at 90%, shift escalation
   - Layer 4 (Cascade): Would this transfer push any Ohio order past its deadline?
3. Agent recommends action: "Transfer", "Transfer with procurement", "Transfer on overtime", or "Non-transferable"
4. Running capacity tracker updates after each approved transfer
5. Agent explains reasoning in natural language, not just pass/fail flags

**Traces to**: FR-06.1 through FR-06.5

### US-08: Approve, Skip, or Reject Order Transfers
**As** Mr. John,
**I want** to approve, skip, or reject each order transfer recommendation and have the agent adapt accordingly,
**So that** I maintain control over every decision while the AI handles the complexity.

**Agent**: Constraint Matching Agent (via Orchestrator)

**Acceptance Criteria**:
1. Side panel shows Approve / Reject / Skip buttons for each order recommendation
2. On Approve: Agent updates running capacity tracker and moves to next order
3. On Skip: Agent moves to next order without updating capacity; skipped order can be revisited later
4. On Reject: Agent marks order as non-transferable and explains the consequence
5. Planner can say "Go back to Order #X" and agent re-evaluates with current capacity state
6. All decisions logged to audit trail with timestamp and rationale

**Traces to**: FR-06.6, FR-06.7, FR-06.8

### US-09: Detect and Flag Cascade Impact
**As** Mr. John,
**I want** the Constraint Matching Agent to detect when transferring a Florida order would push an existing Ohio order past its deadline,
**So that** I don't inadvertently cause a penalty on an existing customer while trying to save another.

**Agent**: Constraint Matching Agent

**Acceptance Criteria**:
1. Agent simulates the updated Ohio schedule after adding each Florida order
2. Agent checks each existing Ohio order's slack (deadline minus estimated completion)
3. If any Ohio order's slack goes negative, agent flags it: "Transferring Order #X would push Ohio Order #Y to Day 21, which is 2 days PAST its deadline. Ohio Order #Y has a penalty clause."
4. Agent recommends whether to proceed or skip based on penalty risk comparison
5. This is the Layer 4 check — the differentiator that ERP systems miss

**Traces to**: FR-06.5

---

## Cross-Cutting Stories

### US-10: View Streaming Agent Responses
**As** Mr. John,
**I want** to see agent responses stream in real-time as the AI thinks,
**So that** I know the system is working and can follow the reasoning as it develops.

**Agent**: All agents (via Orchestrator)

**Acceptance Criteria**:
1. Tokens stream to the UI as the agent generates them (like ChatGPT)
2. Streaming latency < 100ms from backend to UI
3. Structured data (tables, capacity tracker) renders inline as streaming completes
4. UI indicates which agent is currently active
5. "Explain reasoning" sections are expandable for each recommendation

**Traces to**: FR-07.4, FR-07.5, FR-07.6

---

## INVEST Validation

| Story | I | N | V | E | S | T |
|-------|---|---|---|---|---|---|
| US-01 | Yes - standalone alert | Yes - alert format negotiable | Yes - enables rapid response | Yes - 1-2 days | Yes - single interaction | Yes - 5 criteria |
| US-02 | Yes - standalone prioritization | Yes - algorithm tunable | Yes - drives all downstream | Yes - 2-3 days | Yes - one agent output | Yes - 6 criteria |
| US-03 | Yes - optional override | Yes - UI approach flexible | Yes - human control | Yes - 1 day | Yes - single action | Yes - 4 criteria |
| US-04 | Yes - standalone capacity | Yes - dimensions flexible | Yes - feeds constraint matching | Yes - 2-3 days | Yes - one agent output | Yes - 5 criteria |
| US-05 | Yes - optional constraints | Yes - constraint types flexible | Yes - real-world accuracy | Yes - 1-2 days | Yes - single interaction | Yes - 5 criteria |
| US-06 | Yes - standalone delay logic | Yes - criteria negotiable | Yes - frees capacity | Yes - 2-3 days | Yes - one workflow step | Yes - 6 criteria |
| US-07 | Yes - core matching | Yes - layer details flexible | Yes - the core value | Yes - 3-5 days | Yes - one funnel pass | Yes - 5 criteria |
| US-08 | Yes - approval flow | Yes - UI approach flexible | Yes - human control | Yes - 2-3 days | Yes - interaction pattern | Yes - 6 criteria |
| US-09 | Yes - cascade detection | Yes - threshold negotiable | Yes - prevents penalties | Yes - 2-3 days | Yes - one check type | Yes - 5 criteria |
| US-10 | Yes - streaming UI | Yes - streaming approach flexible | Yes - UX quality | Yes - 2-3 days | Yes - one UI feature | Yes - 5 criteria |

---

## Story-to-Requirement Traceability

| Story | Requirements Covered |
|-------|---------------------|
| US-01 | FR-01.1, FR-01.2, FR-01.3, FR-01.4 |
| US-02 | FR-02.1, FR-02.2, FR-02.3, FR-02.4, FR-02.5 |
| US-03 | FR-02.5, FR-02.6, FR-08.1 |
| US-04 | FR-03.1 through FR-03.9 |
| US-05 | FR-03.10, FR-06.9 |
| US-06 | FR-04.1 through FR-04.6, FR-05.1 through FR-05.3 |
| US-07 | FR-06.1 through FR-06.5 |
| US-08 | FR-06.6, FR-06.7, FR-06.8, FR-08.1 |
| US-09 | FR-06.5 |
| US-10 | FR-07.1 through FR-07.6 |
