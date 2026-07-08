# Functional Design Plan — Unit 6: Constraint Matching Agent

## Context
- **Unit**: Unit 6 — Constraint Matching Agent
- **Language**: Python (Strands Agents SDK)
- **Stories**: US-07, US-08, US-09
- **Requirements**: FR-06.1 through FR-06.9
- **Dependencies**: Unit 1 (ERP Data MCP), Unit 3 (Audit MCP), Unit 5 (Capacity & Optimization Agent shared context)

## Execution Steps

- [x] Step 1: Define domain entities (Pydantic models for funnel results, running tracker, cascade impact)
- [x] Step 2: Define business rules (BR-CM-01 through BR-CM-XX)
- [x] Step 3: Define business logic model (4-layer constraint funnel algorithm, order processing flow, running tracker updates)

## Questions

## Question 1: Equipment Compatibility — Gauge Range Handling
Layer 1 checks if Ohio machines can handle the Florida order's product family. Should gauge range (thickness) also be checked, or is product family sufficient for MVP?

A) Product family match only (simpler — if Rolling Mill supports "Steel Coil", any Steel Coil order passes)
B) Product family + gauge range check (order's gauge must fall within machine's min/max range)
C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2: Material Availability — Partial Match Procurement Logic
Layer 2 checks raw material availability. For "Partial Match" (surplus < required but procurement possible), how should procurement feasibility be determined?

A) Simple: procurement_lead_time_days <= days_until_due_date (if material can arrive before deadline, it's a partial match)
B) Conservative: procurement_lead_time_days + production_time_days <= days_until_due_date (material must arrive AND production must complete before deadline)
C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3: Utilization Layer — Shift Escalation Behavior
Layer 3 checks machine utilization. When normal shift hours are insufficient, should the agent automatically escalate to overtime/weekend, or present escalation as a separate recommendation?

A) Auto-escalate: If normal hours insufficient, automatically check overtime, then weekend — present the final shift tier needed
B) Recommend escalation: Present normal-shift shortfall and recommend "Transfer on overtime" or "Transfer on weekend" as separate options for planner approval
C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 4: Cascade Impact — Simulation Depth
Layer 4 simulates adding the Florida order to Ohio's schedule. How deep should the cascade simulation go?

A) Single-level: Check if adding this order pushes any existing Ohio order past its deadline (one pass)
B) Multi-level: Check cascading effects (if Ohio order X is pushed, does that push Ohio order Y, etc.)
C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5: Running Capacity Tracker — Persistence
The running capacity tracker updates after each approved transfer. Where should it be persisted?

A) In-memory only (CapacityState pattern from Unit 5 — fast, lost on restart)
B) DynamoDB via ERP Data MCP (persistent, survives restarts, uses existing update_running_tracker tool)
C) Both: in-memory for speed + DynamoDB for persistence (write-through cache)
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6: Skip/Reorder — Revisit Behavior
When a planner skips an order, US-08 says "skipped order can be revisited later." How should revisit work?

A) Append to end: Skipped orders are added to the end of the queue and processed after all other orders
B) On-demand only: Skipped orders are only revisited if the planner explicitly asks "Go back to Order #X"
C) Both: Skipped orders go to end of queue AND planner can request specific revisit at any time
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 7: Order Recommendation Categories
FR-06.6 says the agent recommends one of: "Transfer", "Transfer with procurement", "Transfer on overtime", or "Non-transferable". Should there be additional categories?

A) Use exactly those 4 categories as specified
B) Add "Transfer on weekend" as a 5th category (distinct from overtime)
C) Add "Transfer with conditions" as a catch-all for complex scenarios (e.g., needs both procurement AND overtime)
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 8: Manpower Check Integration
Layer 3 mentions manpower headcount check. Should manpower be a hard constraint (blocks transfer if insufficient) or a soft warning?

A) Hard constraint: If available operators < required operators, order fails Layer 3
B) Soft warning: Flag insufficient manpower but still allow transfer (planner decides)
C) Tiered: Hard constraint for normal shifts, soft warning for overtime/weekend (assumes temp workers available)
D) Other (please describe after [Answer]: tag below)

[Answer]: C
