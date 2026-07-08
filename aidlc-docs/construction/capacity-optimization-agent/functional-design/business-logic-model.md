# Business Logic Model — Unit 5: Capacity & Optimization Agent

## Overview

The Capacity & Optimization Agent performs three major workflows:
1. Capacity Analysis (US-04) — assess Ohio plant capacity across 5 dimensions
2. Constraint Handling (US-05) — apply planner constraints with immediate recalculation
3. Delay Optimization (US-06) — identify delay candidates, process decisions, recalculate

The agent is invoked by the Orchestrator as a tool call. It runs in Round 1 (parallel with Impact Assessment Agent) for capacity analysis, and in Round 2 for delay optimization.

---

## Workflow 1: Capacity Analysis (US-04)

### Step 1: Fetch All Capacity Data

Agent calls ERP Data MCP tools in parallel:
- `get_machine_capacity(machine_type="Rolling Mill")` -> Rolling Mill capability
- `get_machine_capacity(machine_type="Finishing Line")` -> Finishing Line capability
- `get_manpower()` -> operator availability
- `get_materials()` -> raw material inventory
- `get_orders(plant="Ohio", status="Active")` -> existing Ohio order load
- `get_customers()` -> customer data for penalty clause enrichment

### Step 2: Compute Equipment Capability

For each machine type:
```
net_available_hours_per_week = total_hours_per_week - planned_downtime_hrs_week
net_available_hours_window = net_available_hours_per_week * (rerouting_window_days / 5)
```

Record product families supported, gauge ranges (Rolling Mill), and setup times.

### Step 3: Compute Machine Utilization (Tiered)

For each machine type, compute utilization per shift tier:

```
Normal shift:
  total_hours = utilization data from MCP (normal shift capacity over window)
  committed_hours = sum of machine hours from existing Ohio orders (normal shift)
  surplus_hours = total_hours - committed_hours
  utilization_pct = committed_hours / total_hours * 100

Overtime shift:
  total_hours = availability_pct_overtime * net_available_hours_window
  committed_hours = 0 (overtime not yet committed)
  surplus_hours = total_hours
  utilization_pct = 0

Weekend shift:
  total_hours = availability_pct_weekend * net_available_hours_window
  committed_hours = 0 (weekend not yet committed)
  surplus_hours = total_hours
  utilization_pct = 0
```

Tiered effective surplus: normal surplus is used first. Overtime and weekend
are available but reported separately — they represent escalation capacity.

### Step 4: Compute Manpower Availability

```
available_surplus = total_operators - currently_allocated
max_rolling_mill_shifts = available_surplus / operators_per_rolling_mill
max_finishing_line_shifts = available_surplus / operators_per_finishing_line
```

Report surplus operators and how many additional shifts each machine can support.

### Step 5: Compute Raw Material Surplus

For each material type:
```
available_surplus_tons = current_inventory_tons - committed_to_orders_tons
```

Map product families to material types to determine which Florida orders can be served.

### Step 6: Compute Existing Order Load with Slack

For each Ohio active order:
```
estimated_completion_days = (rolling_mill_hours + finishing_line_hours) / daily_capacity
slack_days = (due_date - today - estimated_completion_days)
```

Enrich with customer penalty_clause from customer data.

### Step 7: Identify Bottleneck (Ratio-Based)

Compute demand from Florida prioritized orders (read from AgentCore Memory if available, otherwise estimate from historical):

```
For each machine type:
  demand_hours = sum of Florida P1 + P2 order hours for this machine
  surplus_hours = normal_surplus + overtime_surplus + weekend_surplus
  surplus_to_demand_ratio = surplus_hours / demand_hours (if demand > 0)

bottleneck = machine with LOWEST surplus_to_demand_ratio
```

If demand_hours is 0 for a machine, its ratio is infinity (not a bottleneck).

Generate natural language explanation:
```
"Rolling Mill is the constraint at {ratio:.0%} capacity coverage
({surplus_hours} surplus hours vs {demand_hours} hours of Florida demand).
Finishing Line has {other_ratio:.0%} coverage."
```

### Step 8: Build Capacity Snapshot

Assemble all 5 dimensions into a CapacitySnapshot object. Write to AgentCore Memory under key `"capacity_snapshot"`.

### Step 9: Present to Planner

Present capacity as structured tables inline in chat:

Table 1 — Equipment Capability:
| Machine | Families | Net Hours/Week | Gauge Range |

Table 2 — Machine Utilization (Tiered):
| Machine | Normal Surplus | OT Available | Weekend Available | Total |

Table 3 — Manpower:
| Total Operators | Allocated | Surplus | Max RM Shifts | Max FL Shifts |

Table 4 — Material Surplus:
| Material | Inventory | Committed | Surplus | Lead Time |

Table 5 — Existing Ohio Load (top orders by slack):
| Order | Family | Due Date | Slack Days | Penalty? |

Bottleneck summary in natural language after tables.

---

## Workflow 2: Constraint Handling (US-05)

### Step 1: Parse Constraint

LLM interprets planner's natural language constraint and classifies:
- `shift_restriction`: "No weekend shifts", "No overtime this week"
- `capacity_limit`: "Cap Rolling Mill at 80%"
- `other`: free-form constraint

### Step 2: Apply Constraint Globally

Constraints apply to the entire capacity snapshot (all machines):

For shift restrictions:
```
if constraint == "No weekend shifts":
    for each machine:
        weekend.total_hours = 0
        weekend.surplus_hours = 0
        recalculate total_surplus and effective_surplus
```

For capacity limits:
```
if constraint == "Cap Rolling Mill at 80%":
    rolling_mill.normal.total_hours *= 0.80
    recalculate surplus and utilization_pct
```

### Step 3: Recalculate Bottleneck

Re-run bottleneck identification with updated surplus values.

### Step 4: Present Before/After Comparison

```
"Applying 'No weekend shifts':
 - Rolling Mill: surplus drops from 45 hrs to 20 hrs (-25 hrs)
 - Finishing Line: surplus drops from 140 hrs to 80 hrs (-60 hrs)
 - New bottleneck: Rolling Mill (ratio: 0.14 vs 0.57)
 - Impact: 25 fewer Rolling Mill hours available for Florida transfers"
```

### Step 5: Store Constraint

Add constraint to `active_constraints` list in CapacitySnapshot. Update AgentCore Memory.

### What-If Handling

When planner asks "What if I authorize weekend shifts for 3 weeks?":
1. Temporarily remove the weekend restriction
2. Recalculate with weekend shifts enabled for 3 weeks
3. Present comparison WITHOUT persisting (what-if is exploratory)
4. If planner confirms, persist the change

---

## Workflow 3: Delay Optimization (US-06)

### Step 1: Identify Delay Candidates

Filter existing Ohio orders:
```
candidates = [
    order for order in ohio_orders
    if order.priority == "P3"
    and order.slack_days > delay_threshold_days
]
```

Sort candidates by freed capacity (descending) — orders that free the most bottleneck capacity first.

### Step 2: Calculate Freed Capacity Per Candidate

For each candidate, report all 4 dimensions:
```
freed_rolling_mill_hours = order.rolling_mill_hours
freed_finishing_line_hours = order.finishing_line_hours
freed_material_tons = order.raw_material_tons
freed_operator_hours = (order.rolling_mill_hours * operators_per_rolling_mill
                       + order.finishing_line_hours * operators_per_finishing_line)
remaining_buffer_days = order.slack_days - delay_threshold_days
```

Assess risk:
```
if remaining_buffer_days > 21: risk = "Low"
elif remaining_buffer_days > 7: risk = "Medium"
else: risk = "High"
```

Generate trade-off explanation:
```
"Order PO-2026-015 frees 30 Rolling Mill hours and 15 Finishing Line hours.
22-day buffer remains after delay. Low risk. Customer has no penalty clause."
```

### Step 3: Present Candidates to Planner

Present each candidate with:
- Order details (ID, family, customer, due date, value)
- Freed capacity breakdown (4 dimensions)
- Remaining buffer and risk level
- Trade-off explanation
- Approve / Reject buttons

### Step 4: Process Each Decision (Immediate Recalculation)

After EACH planner decision:

If approved:
```
1. Add order_id to delays_approved list
2. Add freed capacity back to surplus:
   surplus.rolling_mill += freed_rolling_mill_hours
   surplus.finishing_line += freed_finishing_line_hours
   surplus.material += freed_material_tons
   surplus.manpower += freed_operators
3. Recalculate bottleneck with new surplus
4. Update CapacitySnapshot in AgentCore Memory
5. Present updated surplus to planner
6. Write audit entry via Audit MCP
```

If rejected:
```
1. Log rejection
2. Recalculate remaining candidates' impact (surplus unchanged)
3. Communicate downstream impact:
   "Rejecting delay of PO-2026-015 means 30 fewer Rolling Mill hours
    available. This may reduce the number of Florida orders transferable."
4. Write audit entry via Audit MCP
```

### Step 5: Present Before/After Summary

After all delay decisions:
```
"Delay optimization complete:
 - 3 of 5 candidates approved
 - Rolling Mill surplus: 45 hrs -> 105 hrs (+60 hrs)
 - Finishing Line surplus: 140 hrs -> 175 hrs (+35 hrs)
 - Material freed: 45 tons
 - Bottleneck shifted from Rolling Mill (0.32) to balanced (0.75 vs 0.78)
 
Ready for constraint matching."
```

Update AgentCore Memory with final post-delay capacity snapshot.

---

## Agent Tool Bindings

| MCP Server | Tool | Purpose |
|------------|------|---------|
| ERP Data MCP | `get_machine_capacity` | Fetch Rolling Mill / Finishing Line data |
| ERP Data MCP | `get_manpower` | Fetch operator availability |
| ERP Data MCP | `get_materials` | Fetch raw material inventory |
| ERP Data MCP | `get_orders` | Fetch existing Ohio orders |
| ERP Data MCP | `get_customers` | Fetch customer penalty clause data |
| Audit MCP | `write_audit_entry` | Log delay decisions and constraint changes |

---

## Shared Context Output

After capacity analysis + delay optimization, writes to AgentCore Memory:

Key: `"capacity_snapshot"` — full CapacitySnapshot (see domain-entities.md)

Consumed by:
- Constraint Matching Agent (Unit 6) — reads surplus for funnel layer 3 (utilization check)
- Orchestrator Agent (Unit 7) — reads bottleneck for summary generation
