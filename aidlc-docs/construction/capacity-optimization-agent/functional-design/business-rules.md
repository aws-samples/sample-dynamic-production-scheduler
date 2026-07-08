# Business Rules — Unit 5: Capacity & Optimization Agent

## BR-CO-01: Input Scope

- Agent ONLY analyzes Ohio plant capacity and Ohio active orders
- Florida orders are never loaded by this agent (they come from shared context)
- Agent reads Ohio data via ERP Data MCP tools

## BR-CO-02: Rerouting Window

- Default: 10 business days (configurable via `REROUTING_WINDOW_DAYS` env var)
- All surplus calculations are scoped to this window
- Capacity beyond the window is not considered

## BR-CO-03: Tiered Utilization Model

- Surplus is reported per shift tier: Normal, Overtime, Weekend
- Normal shift surplus is consumed first before escalating
- Overtime is available only after normal surplus is exhausted
- Weekend is available only after overtime is exhausted
- Each tier is reported separately in presentation tables
- `effective_surplus` = normal_surplus (primary), OT and weekend are escalation

## BR-CO-04: Bottleneck Identification (Ratio-Based)

- Bottleneck = machine with the LOWEST surplus-to-demand ratio
- Ratio = total_surplus_hours / florida_demand_hours
- Florida demand = sum of P1 + P2 order hours for that machine type
- If Florida demand is 0 for a machine, ratio = infinity (not a bottleneck)
- If both machines have equal ratio, Rolling Mill is the tiebreaker (harder to scale)

## BR-CO-05: Utilization Warning Threshold

- When any machine's normal shift utilization exceeds 90% (configurable), flag a warning
- Warning text: "{machine_type} normal shift at {pct}% utilization — overtime escalation likely"
- This is informational only — does not block any workflow

## BR-CO-06: Delay Candidate Eligibility

- Ohio order must have priority = "P3" (or null/unclassified)
- Ohio order must have slack_days > delay_threshold_days (default 42, configurable)
- Orders with penalty_clause = true are EXCLUDED from delay candidates
- Orders already in "Delayed" or "Cancelled" status are excluded

## BR-CO-07: Delay Candidate Sort Order

- Primary sort: descending by freed bottleneck machine hours (most impactful first)
- Secondary sort: descending by total freed hours (both machines)
- Tiebreaker: ascending by due_date (later due date = safer to delay)

## BR-CO-08: Freed Capacity Calculation

- All 4 dimensions reported per candidate:
  - Rolling Mill hours: order.rolling_mill_hours
  - Finishing Line hours: order.finishing_line_hours
  - Material tons: order.raw_material_tons
  - Operator hours: (RM hours * operators_per_RM) + (FL hours * operators_per_FL)
- Freed capacity is the exact resource allocation of the delayed order

## BR-CO-09: Risk Assessment for Delay Candidates

- remaining_buffer = slack_days - delay_threshold_days
- If remaining_buffer > 21 days: "Low" risk
- If remaining_buffer > 7 days: "Medium" risk
- If remaining_buffer <= 7 days: "High" risk
- Risk is informational — planner makes final decision

## BR-CO-10: Immediate Recalculation Per Decision

- After EACH delay approval: add freed capacity to surplus, recalculate bottleneck
- After EACH delay rejection: surplus unchanged, communicate downstream impact
- Do NOT batch decisions — each decision triggers immediate recalculation
- Updated surplus is persisted to AgentCore Memory after each decision

## BR-CO-11: Constraint Application — Global Scope

- All planner constraints apply globally (all machines, all shift types)
- Constraints are cumulative — multiple constraints can be active simultaneously
- Removing a constraint requires explicit planner request
- Constraint application triggers immediate recalculation of all surplus values

## BR-CO-12: Constraint Types

- `shift_restriction`: zeroes out the specified shift tier's hours
  - "No weekend shifts" -> weekend.total_hours = 0 for all machines
  - "No overtime" -> overtime.total_hours = 0 for all machines
- `capacity_limit`: applies percentage cap to specified capacity
  - "Cap at 80%" -> total_hours *= 0.80 for affected tier
- `other`: LLM interprets and applies best-fit logic, explains to planner

## BR-CO-13: What-If vs Persist

- What-if scenarios are exploratory — they do NOT update AgentCore Memory
- What-if results are presented as comparison only
- Planner must explicitly confirm to persist a what-if scenario
- If confirmed, the what-if becomes the active state

## BR-CO-14: No Ohio Orders Found

- If `get_orders(plant="Ohio", status="Active")` returns empty list:
  - Report "No active Ohio orders. Full capacity available for Florida transfers."
  - Existing load = 0, all surplus = full capacity
  - No delay candidates (nothing to delay)

## BR-CO-15: MCP Tool Failure Handling

- If `get_machine_capacity` fails: agent reports error and halts (capacity is core)
- If `get_manpower` fails: proceed with manpower dimension marked "unavailable"
- If `get_materials` fails: proceed with materials dimension marked "unavailable"
- If `get_orders` fails: agent reports error and halts (order load is core)
- If `get_customers` fails: proceed without penalty_clause data (default false)
- If Audit MCP fails: log warning, continue workflow (audit gap noted)

## BR-CO-16: Audit Logging Rules

- Capacity analysis completion: one audit entry with summary
  - action: "capacity_analysis"
  - details: bottleneck, surplus summary, constraint count
- Each delay decision: one audit entry
  - action: "delay_approved" or "delay_rejected"
  - details: order_id, freed capacity (if approved), reason
- Each constraint applied: one audit entry
  - action: "constraint_applied"
  - details: constraint_text, before/after surplus delta
- All entries use session_id from current workflow session

## BR-CO-17: Slack Calculation

- slack_days = (due_date - today).days - estimated_production_days
- estimated_production_days = max(rolling_mill_hours, finishing_line_hours) / daily_machine_hours
- daily_machine_hours = net_available_hours_per_week / 5
- If slack_days < 0, order is at risk of missing deadline (flag in output)

## BR-CO-18: Post-Delay Capacity Snapshot

- After all delay decisions are processed, the final CapacitySnapshot includes:
  - Updated surplus (with freed capacity from approved delays)
  - Updated bottleneck (recalculated with new surplus)
  - List of approved delay order IDs
  - All active constraints
- This is the snapshot consumed by Constraint Matching Agent (Unit 6)
