# Business Logic Model — Unit 6: Constraint Matching Agent

## Overview

The Constraint Matching Agent processes Florida orders one at a time through a 4-layer constraint funnel, presenting each order to the Planner with a transfer recommendation. It maintains a running capacity tracker that updates after each decision, ensuring subsequent orders are evaluated against current available capacity. The agent is invoked by the Orchestrator during Round 2, after the Capacity & Optimization Agent completes delay processing.

---

## Order Processing Flow

### Step 1: Initialize

Agent reads from shared context and ERP Data MCP:
- `prioritized_orders` from AgentCore Memory (Unit 4 output) → Florida order queue
- `capacity_snapshot` from AgentCore Memory (Unit 5 output) → initial capacity state
- `get_running_tracker(session_id)` from ERP Data MCP → existing tracker (if resuming)
- `get_machine_capacity()` → equipment capability for Layer 1
- `get_materials()` → material inventory for Layer 2
- `get_orders(plant="Ohio", status="Active")` → Ohio schedule for Layer 4
- `get_manpower()` → manpower data for Layer 3

If no existing tracker found, initialize from capacity snapshot:
```
tracker.rolling_mill_remaining_hrs = {
    normal: surplus_summary.rolling_mill_normal_hrs,
    overtime: surplus_summary.rolling_mill_overtime_hrs,
    weekend: surplus_summary.rolling_mill_weekend_hrs
}
tracker.finishing_line_remaining_hrs = {
    normal: surplus_summary.finishing_line_normal_hrs,
    overtime: surplus_summary.finishing_line_overtime_hrs,
    weekend: surplus_summary.finishing_line_weekend_hrs
}
tracker.material_remaining_tons = surplus_summary.total_material_surplus_tons
tracker.manpower_remaining = surplus_summary.total_manpower_surplus
```

### Step 2: Build Priority Queue

Sort Florida orders into processing queue:
1. All P1 orders (descending by weighted_score, tiebreak by due_date asc, then order_id asc)
2. All P2 orders (same sort)
3. All P3 orders (same sort)

Skip any orders already in `tracker.orders_processed` (session resumption).

### Step 3: Process Next Order (Loop)

For each order in the queue, run the 4-layer constraint funnel:

---

## 4-Layer Constraint Funnel Algorithm

### Layer 1: Equipment Compatibility

```
Input: order.product_family, order.gauge (if applicable)
Data: equipment capabilities from ERP Data MCP

For each machine_type in ["Rolling Mill", "Finishing Line"]:
    if order.product_family NOT IN machine.product_families_supported:
        layer1.passed = False
        layer1.failure_reason = "{product_family} not supported by {machine_type}"
        break

If Rolling Mill has gauge_range_min and gauge_range_max:
    if order.gauge < gauge_range_min OR order.gauge > gauge_range_max:
        layer1.passed = False
        layer1.gauge_in_range = False
        layer1.failure_reason = "Gauge {gauge}mm outside range [{min}-{max}mm]"

If all checks pass:
    layer1.passed = True
```

### Layer 2: Material Availability

```
Input: order.raw_material_tons, order.due_date
Data: tracker.material_remaining_tons, material procurement data

required = order.raw_material_tons
available = tracker.material_remaining_tons

if available >= required:
    match_status = "Full Match"
    layer2.passed = True
else:
    shortfall = required - available
    procurement_days = material.procurement_lead_time_days
    production_days = max(order.rolling_mill_hours, order.finishing_line_hours)
                      / daily_machine_hours
    days_until_due = (order.due_date - today).days

    if procurement_days + production_days <= days_until_due:
        match_status = "Partial Match"
        layer2.passed = True  (with procurement condition)
        layer2.procurement_feasible = True
    else:
        match_status = "No Match"
        layer2.passed = False
        layer2.failure_reason = "Procurement ({procurement_days}d) + production
            ({production_days}d) = {total}d exceeds {days_until_due}d to deadline"
```

### Layer 3: Machine Utilization + Manpower

```
Input: order.rolling_mill_hours, order.finishing_line_hours
Data: tracker.rolling_mill_remaining_hrs, tracker.finishing_line_remaining_hrs,
      tracker.manpower_remaining

For each machine in [Rolling Mill, Finishing Line]:
    required_hrs = order.{machine}_hours
    available_normal = tracker.{machine}_remaining_hrs.normal_hrs

    if available_normal >= required_hrs:
        recommended_tier = "Normal"
        escalation_needed = False
    else:
        escalation_needed = True
        available_ot = tracker.{machine}_remaining_hrs.overtime_hrs
        available_wk = tracker.{machine}_remaining_hrs.weekend_hrs

        Build escalation options:
        - Option 1: "Transfer on overtime" (if normal + OT >= required)
        - Option 2: "Transfer on weekend" (if normal + OT + weekend >= required)

        if normal + OT + weekend < required:
            layer3.passed = False
            layer3.failure_reason = "Insufficient {machine} hours across all shifts"

Manpower check:
    required_operators = (RM_hrs * operators_per_RM) + (FL_hrs * operators_per_FL)
    if recommended_tier == "Normal":
        if tracker.manpower_remaining < required_operators:
            layer3.passed = False  (HARD constraint)
            layer3.failure_reason = "Insufficient operators for normal shift"
    else:  # Overtime or Weekend
        if tracker.manpower_remaining < required_operators:
            layer3.manpower_constraint_type = "soft"
            layer3.manpower_note = "Temp workers may be needed for {tier} shift"

Utilization warning:
    post_transfer_pct = (committed + required) / total * 100
    if post_transfer_pct > 90:
        layer3.utilization_warning = True
```

### Layer 4: Cascade Impact Simulation

```
Input: order.rolling_mill_hours, order.finishing_line_hours
Data: Ohio active orders (sorted by schedule position), max_cascade_depth

Step 4a: Insert Florida order at END of Ohio schedule
    ohio_schedule = sorted(ohio_orders, by=schedule_position)
    ohio_schedule.append(florida_order)

Step 4b: Recalculate completion times for all orders after insertion point
    For each order in ohio_schedule (from insertion point onward):
        completion_hours = sum of all preceding order hours + this order hours
        completion_days = completion_hours / daily_machine_hours
        new_slack = (order.due_date - today).days - completion_days

        if new_slack < 0:
            Mark as impacted (cascade_level = 1)

Step 4c: Multi-level cascade (depth 2+)
    For each impacted order at level N (up to max_cascade_depth):
        Check if this order's delay pushes subsequent orders
        If yes, mark those as impacted at level N+1

Step 4d: Assess impact severity
    if no orders impacted:
        layer4.passed = True
    elif impacted orders exist but NONE have penalty_clause:
        layer4.passed = True (soft warning)
        layer4.explanation = "Warning: {count} Ohio orders impacted but no penalty risk"
    elif any impacted order has penalty_clause:
        layer4.passed = False
        layer4.has_penalty_risk = True
        layer4.failure_reason = "Ohio order {id} with penalty clause pushed
            {days} days past deadline"
```

---

## Recommendation Generation

After all 4 layers are evaluated:

```
if any layer has hard failure:
    recommendation = NON_TRANSFERABLE
elif layer2.match_status == "Partial Match" AND layer3.escalation_needed:
    recommendation = TRANSFER_WITH_CONDITIONS
    conditions = ["Requires procurement", "Requires {tier} shift"]
elif layer2.match_status == "Partial Match":
    recommendation = TRANSFER_WITH_PROCUREMENT
    conditions = ["Requires procurement ({lead_time} days)"]
elif layer3.escalation_needed AND recommended_tier == "Weekend":
    recommendation = TRANSFER_ON_WEEKEND
elif layer3.escalation_needed AND recommended_tier == "Overtime":
    recommendation = TRANSFER_ON_OVERTIME
else:
    recommendation = TRANSFER
```

---

## Agent Presentation Logic

### Per-Order Presentation

Agent presents each order to the Planner:

```
"Order PO-2026-003 (P1 — Steel Coils, Acme Manufacturing, Tier1)
Due: 2026-03-25 | Qty: 500 | Value: $180,000

Constraint Funnel Results:
  Layer 1 (Equipment):  PASS — Rolling Mill and Finishing Line support Steel Coils,
                        gauge 2.5mm within range [1.0-5.0mm]
  Layer 2 (Material):   PARTIAL MATCH — 80 of 120 tons available,
                        procurement feasible (5d lead + 3d production = 8d < 12d to deadline)
  Layer 3 (Utilization): PASS on Overtime — Normal shift 5hrs short on Rolling Mill,
                         12hrs available on overtime. Manpower: soft warning for OT shift.
  Layer 4 (Cascade):    PASS — No Ohio orders impacted at any cascade level.

Recommendation: TRANSFER WITH CONDITIONS
  - Requires procurement of 40 tons (5-day lead time)
  - Requires overtime shift on Rolling Mill

Approve / Skip / Reject?"
```

---

## Decision Processing

### On Approve

```
1. Deduct capacity from running tracker:
   - RM hours: consume from normal first, then OT, then weekend
   - FL hours: same tiered consumption
   - Material: deduct raw_material_tons
   - Manpower: deduct operator hours
2. Add order to tracker.orders_approved
3. Add ProcessedOrderEntry to tracker.orders_processed
4. Persist tracker to DynamoDB via update_running_tracker
5. Write audit entry (action: "order_decision", details: approved + capacity consumed)
6. Present updated capacity summary
7. Move to next order in queue
```

### On Reject

```
1. No tracker update (capacity unchanged)
2. Add order to tracker.orders_rejected
3. Add ProcessedOrderEntry to tracker.orders_processed (decision: "rejected")
4. Persist tracker to DynamoDB
5. Write audit entry (action: "order_decision", details: rejected)
6. Present: "Order {id} marked as non-transferable. Capacity unchanged."
7. Move to next order in queue
```

### On Skip

```
1. No tracker update (capacity unchanged)
2. Add order_id to tracker.orders_skipped
3. Append order_id to END of processing queue
4. Add ProcessedOrderEntry to tracker.orders_processed (decision: "skipped")
5. Persist tracker to DynamoDB
6. Write audit entry (action: "order_skip")
7. Present: "Order {id} skipped. It will be revisited after remaining orders."
8. Move to next order in queue
```

### On Revisit Request ("Go back to Order #X")

```
1. Remove order from skip queue (if present)
2. Re-run full 4-layer funnel with CURRENT tracker state
3. Present updated funnel results and recommendation
4. Planner can approve/reject/skip again
5. Write audit entry (action: "order_revisit")
```

---

## Running Tracker Update — Tiered Hour Consumption

When deducting hours for an approved order:

```
def consume_hours(tracker_machine_hrs, required_hrs):
    remaining = required_hrs

    # Consume normal first
    normal_consumed = min(tracker_machine_hrs.normal_hrs, remaining)
    tracker_machine_hrs.normal_hrs -= normal_consumed
    remaining -= normal_consumed

    # Then overtime
    if remaining > 0:
        ot_consumed = min(tracker_machine_hrs.overtime_hrs, remaining)
        tracker_machine_hrs.overtime_hrs -= ot_consumed
        remaining -= ot_consumed

    # Then weekend
    if remaining > 0:
        wk_consumed = min(tracker_machine_hrs.weekend_hrs, remaining)
        tracker_machine_hrs.weekend_hrs -= wk_consumed
        remaining -= wk_consumed

    # Update total
    tracker_machine_hrs.total_hrs = (
        tracker_machine_hrs.normal_hrs
        + tracker_machine_hrs.overtime_hrs
        + tracker_machine_hrs.weekend_hrs
    )

    return remaining  # should be 0 if Layer 3 passed
```

---

## Agent Tool Bindings

| MCP Server | Tool | Purpose |
|------------|------|---------|
| ERP Data MCP | `get_machine_capacity` | Equipment capability for Layer 1 |
| ERP Data MCP | `get_materials` | Material inventory for Layer 2 |
| ERP Data MCP | `get_orders` | Ohio active orders for Layer 4 cascade |
| ERP Data MCP | `get_manpower` | Manpower data for Layer 3 |
| ERP Data MCP | `get_running_tracker` | Load persisted tracker (session resumption) |
| ERP Data MCP | `update_running_tracker` | Persist tracker after each decision |
| Audit MCP | `write_audit_entry` | Log funnel evaluations and decisions |

---

## Shared Context Consumption

The agent reads (but does not write) these shared context keys:

| Key | Source | Content |
|-----|--------|---------|
| `prioritized_orders` | Unit 4 (Impact Assessment) | Florida orders with P1/P2/P3 and scores |
| `capacity_snapshot` | Unit 5 (Capacity & Optimization) | Post-delay surplus, bottleneck, constraints |

---

## End-of-Queue Behavior

When all orders in the queue have been processed (including skipped orders that cycled back):

```
1. Present transfer summary:
   - Total orders evaluated
   - Orders approved / rejected / skipped (still in skip queue)
   - Total capacity consumed vs remaining
   - Natural language summary

2. If orders remain in skip queue:
   "3 orders remain skipped. Would you like to revisit any of them,
    or finalize the transfer plan?"

3. Write final audit entry (action: "tracker_update")
4. Return control to Orchestrator
```
