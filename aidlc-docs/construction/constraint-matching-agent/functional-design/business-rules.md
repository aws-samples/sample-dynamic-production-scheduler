# Business Rules — Unit 6: Constraint Matching Agent

## BR-CM-01: Input Scope and Processing Order

- Agent processes ONLY Florida orders from shared context (`prioritized_orders`)
- Orders are processed in strict priority order: all P1 first, then P2, then P3
- Within each priority group: descending by weighted_score
- Tiebreaker: ascending by due_date (earlier due date first)
- If due_date also ties: ascending by order_id (deterministic)

## BR-CM-02: 4-Layer Constraint Funnel — Execution Order

- Every order MUST pass through all 4 layers in sequence: L1 → L2 → L3 → L4
- If any layer hard-fails, remaining layers are still evaluated (for informational completeness)
- All 4 layer results are presented to the Planner regardless of pass/fail
- Final recommendation is derived from the composite result of all 4 layers

## BR-CM-03: Layer 1 — Equipment Compatibility (Product Family + Gauge)

- Check if Rolling Mill supports the order's product family
- Check if Finishing Line supports the order's product family
- If Rolling Mill has gauge_range_min/max defined, check order's gauge falls within range
- Pass: product family supported by both machines AND gauge in range
- Fail: product family not supported OR gauge out of range
- Failure is a HARD fail — order cannot be transferred if equipment is incompatible

## BR-CM-04: Layer 2 — Material Availability (Conservative Procurement)

- Compare order's `raw_material_tons` against available surplus from running tracker
- **Full Match**: available_surplus_tons >= required_tons → PASS
- **Partial Match**: surplus < required BUT `procurement_lead_time_days + production_time_days <= days_until_due_date` → PASS (with condition)
- **No Match**: surplus insufficient AND procurement + production exceeds deadline → FAIL
- Production time = `max(rolling_mill_hours, finishing_line_hours) / daily_machine_hours`
- `daily_machine_hours` = `net_available_hours_per_week / 5`
- Partial Match is a SOFT pass — order can transfer but requires procurement (flagged as condition)
- No Match is a HARD fail

## BR-CM-05: Layer 3 — Machine Utilization (Tiered Shift Escalation)

- Check available hours on BOTH Rolling Mill AND Finishing Line from running tracker
- Normal shift hours are consumed first
- If normal hours insufficient, calculate shortfall and present escalation options:
  - Overtime hours available
  - Weekend hours available
- Agent does NOT auto-escalate — presents escalation as separate recommendation options
- 90% utilization warning: if any machine exceeds 90% utilization after transfer, flag warning
- Pass: sufficient hours available (on any shift tier)
- Fail: insufficient hours even with all shift tiers combined

## BR-CM-06: Layer 3 — Manpower Check (Tiered Constraint)

- Calculate required operators: `(RM_hours * operators_per_RM + FL_hours * operators_per_FL)`
- For Normal shifts: manpower is a HARD constraint — if available_surplus < required, Layer 3 fails
- For Overtime/Weekend shifts: manpower is a SOFT warning — flag "temp workers may be needed" but do not fail
- Manpower check uses running tracker's `manpower_remaining` (decremented after each approval)

## BR-CM-07: Layer 4 — Cascade Impact (Multi-Level Simulation)

- Simulate adding the Florida order to Ohio's schedule
- Check ALL existing Ohio orders for deadline violations (slack goes negative)
- Multi-level cascade: if pushing order X causes order Y to slip, check if Y's slip causes Z to slip, etc.
- Maximum cascade depth: configurable (default 5 levels)
- For each impacted order, record: order_id, original_slack, new_slack, days_past_deadline, penalty_clause, cascade_level
- Pass: no Ohio orders pushed past deadline at any cascade level
- Soft fail: Ohio orders impacted but none have penalty clauses → present warning, recommend proceed with caution
- Hard fail: Ohio order with penalty_clause pushed past deadline → recommend skip/reject

## BR-CM-08: Recommendation Category Assignment

- If any layer HARD-fails → `NON_TRANSFERABLE`
- If multiple conditions exist (e.g., procurement needed AND overtime needed) → `TRANSFER_WITH_CONDITIONS`
- If Layer 2 = Partial Match only (no other conditions) → `TRANSFER_WITH_PROCUREMENT`
- If Layer 3 needs overtime only → `TRANSFER_ON_OVERTIME`
- If Layer 3 needs weekend only → `TRANSFER_ON_WEEKEND`
- If all layers pass on normal shift with full material match → `TRANSFER`
- `TRANSFER_WITH_CONDITIONS` is the catch-all for complex multi-condition scenarios

## BR-CM-09: Running Capacity Tracker — Update Rules

- On APPROVE: deduct consumed capacity from running tracker
  - Rolling Mill hours: deduct from appropriate shift tier (normal first, then OT, then weekend)
  - Finishing Line hours: same tiered deduction
  - Material tons: deduct from material_remaining_tons
  - Manpower: deduct operator hours from manpower_remaining
- On REJECT: no tracker update; order marked as non-transferable
- On SKIP: no tracker update; order added to skip queue
- Tracker is persisted to DynamoDB via `update_running_tracker` MCP tool after EVERY decision

## BR-CM-10: Running Capacity Tracker — Initialization

- On first invocation, initialize tracker from Unit 5's shared capacity snapshot:
  - `rolling_mill_remaining_hrs` = surplus from SurplusSummary (normal/OT/weekend)
  - `finishing_line_remaining_hrs` = surplus from SurplusSummary
  - `material_remaining_tons` = total_material_surplus_tons
  - `manpower_remaining` = total_manpower_surplus
- If existing tracker found in DynamoDB (session resumption), load it instead
- Tracker includes list of already-processed orders to avoid double-processing

## BR-CM-11: Skip and Revisit Behavior

- When planner skips an order, it is appended to the END of the processing queue
- Skipped orders are re-evaluated when reached again (with current running capacity state)
- Planner can also request on-demand revisit: "Go back to Order #X"
  - Agent re-runs the full 4-layer funnel with current tracker state
  - If order was previously skipped, it is removed from the skip queue
- An order can be skipped multiple times (re-appended each time)
- Skip does NOT count as a rejection — order remains eligible for transfer

## BR-CM-12: Shift Tier Consumption Order

- When deducting hours from running tracker, consume in strict order:
  1. Normal shift hours (consume first)
  2. Overtime hours (only after normal exhausted)
  3. Weekend hours (only after overtime exhausted)
- This applies independently to Rolling Mill and Finishing Line
- The recommended shift tier in the presentation reflects which tier will actually be consumed

## BR-CM-13: MCP Tool Failure Handling

- If `get_machine_capacity` fails: agent reports error and halts (equipment data is core for Layer 1)
- If `get_materials` fails: Layer 2 defaults to "No Match" with warning "Material data unavailable"
- If `get_orders(plant="Ohio")` fails: Layer 4 cascade check defaults to PASS with warning "Ohio schedule unavailable — cascade not verified"
- If `get_manpower` fails: manpower check defaults to SOFT warning "Manpower data unavailable"
- If `get_running_tracker` fails: initialize fresh tracker from shared context snapshot
- If `update_running_tracker` fails: log warning, continue with in-memory tracker (audit gap noted)
- If Audit MCP `write_audit_entry` fails: log warning, continue workflow (audit gap noted)

## BR-CM-14: Audit Logging Rules

- Every funnel evaluation: one audit entry with action `funnel_evaluation`
  - details: order_id, priority, layer results (pass/fail per layer), recommendation_category
- Every planner decision: one audit entry with action `order_decision`
  - details: order_id, action (approve/reject/skip), capacity_consumed (if approved)
- Every skip: one audit entry with action `order_skip`
  - details: order_id, queue_position
- Every revisit: one audit entry with action `order_revisit`
  - details: order_id, previous_recommendation, new_recommendation
- Every tracker persistence: one audit entry with action `tracker_update`
  - details: orders_approved count, capacity_remaining summary
- All entries use session_id from current workflow session

## BR-CM-15: No Orders to Process

- If shared context `prioritized_orders` is empty or missing:
  - Agent responds: "No prioritized Florida orders found. Nothing to match."
  - No funnel evaluation, no tracker initialization, no audit entry
  - Agent returns control to Orchestrator immediately

## BR-CM-16: Cascade Simulation — Schedule Model

- Ohio schedule is modeled as a simple sequential queue per machine type
- Each order occupies `rolling_mill_hours` on Rolling Mill and `finishing_line_hours` on Finishing Line
- Adding a Florida order inserts it at the END of the current schedule
- Completion time = sum of all preceding order hours + this order's hours
- Slack recalculation: `new_slack = (due_date - today).days - (completion_position_hours / daily_hours)`
- If new_slack < 0, order is past deadline → cascade impact detected
- Multi-level: if order X is pushed, recalculate all orders after X in the queue

## BR-CM-17: Equipment Gauge Range Check

- Only applies to Rolling Mill (Finishing Line does not have gauge constraints)
- If Rolling Mill has `gauge_range_min` and `gauge_range_max` defined:
  - Order must specify a gauge value (derived from product family specifications)
  - If order gauge < gauge_range_min OR order gauge > gauge_range_max → equipment fail
- If Rolling Mill does NOT have gauge range defined: skip gauge check (product family match only)
- Gauge values are in millimeters (mm)
