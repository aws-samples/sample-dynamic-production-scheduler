# Business Rules — Unit 4: Impact Assessment Agent

## BR-IA-01: Input Scope

- Agent ONLY processes Florida plant orders with status "Active"
- Ohio orders are never evaluated by this agent
- Orders with status Delayed/Transferred/Cancelled are excluded

## BR-IA-02: Scoring Normalization

- All 4 criteria are normalized to a 0-100 integer scale before weighting
- Urgency score uses discrete brackets (not linear interpolation)
- Customer tier score uses fixed mapping (Tier1=100, Tier2=60, Tier3=25)
- Order value score uses min-max normalization across the current order set
- Machine complexity score uses fixed mapping based on machine count

## BR-IA-03: Configurable Weights

- Default weights: urgency=0.40, customer_tier=0.25, order_value=0.20, machine_complexity=0.15
- Weights MUST sum to 1.0 (validation enforced)
- Weights are stored in agent configuration (Python dict or environment variable)
- Planner can request weight changes via Orchestrator (what-if scenario)
- When weights change, full re-classification is triggered on all non-pinned orders

## BR-IA-04: Configurable Thresholds

- Default thresholds: P1 >= 75, P2 >= 50, P3 < 50
- Thresholds must satisfy: P1_THRESHOLD > P2_THRESHOLD > 0
- Planner can request threshold changes via Orchestrator
- When thresholds change, full re-classification is triggered on all non-pinned orders

## BR-IA-05: Reclassification — Manual Pin Behavior

- When Planner overrides an order's priority, set `manually_classified = true`
- Manually classified orders are pinned — they are excluded from all subsequent re-evaluations
- Original priority and new priority MUST be recorded for audit trail
- A pinned order can be re-pinned to a different priority (updates the pin, does not unpin)

## BR-IA-06: Reclassification — Re-evaluation Scope

- After a manual override, re-run classification ONLY on orders where `manually_classified = false`
- Re-evaluation uses the same weights and thresholds as the original run
- If re-evaluation changes any order's priority, those changes are persisted and audited
- Re-evaluation does NOT cascade (one pass only — no recursive re-evaluation)

## BR-IA-07: Sort Order Rules

- Primary sort: Priority group (P1 first, P2 second, P3 third)
- Secondary sort: Descending by weighted_score within each group
- Tiebreaker: Ascending by due_date (earlier due date wins)
- If due_date also ties: Ascending by order_id (deterministic output)

## BR-IA-08: Weight Validation

- All 4 weights MUST be non-negative floats
- Weights MUST sum to exactly 1.0 (tolerance: ±0.001 for floating point)
- If weight sum is outside tolerance, reject with error before scoring
- Individual weight of 0.0 is allowed (disables that criterion)

## BR-IA-09: Threshold Validation

- P1_THRESHOLD and P2_THRESHOLD MUST be integers between 1 and 99
- P1_THRESHOLD MUST be strictly greater than P2_THRESHOLD
- If thresholds violate ordering, reject with error before scoring
- Thresholds apply to the weighted_score (0-100 scale)

## BR-IA-10: Order Value Normalization Edge Case

- If all orders in the set have identical order_value, set value_score = 50 for all
- If only one order exists, set value_score = 50 (no meaningful min-max)
- min_value and max_value are computed from the current active order set only

## BR-IA-11: Overdue Order Handling

- Orders with `days_remaining <= 0` receive urgency_score = 100
- Overdue orders are NOT automatically classified as P1 — they still go through weighted scoring
- An overdue order with a Tier3 customer and low value could still be P2 or P3

## BR-IA-12: No Orders Found

- If `get_orders(plant="Florida", status="Active")` returns empty list, agent responds:
  "No active Florida orders found. Nothing to prioritize."
- No scoring, no shared context write, no audit entry for classification
- Agent returns control to Orchestrator immediately

## BR-IA-13: MCP Tool Failure Handling

- If ERP Data MCP `get_orders` fails, agent reports error to Orchestrator and halts
- If ERP Data MCP `get_customers` fails, agent proceeds WITHOUT customer tier enrichment
  - Customer tier score defaults to 50 (neutral) for all orders
  - Agent includes warning in output: "Customer data unavailable — tier scores defaulted"
- If Audit MCP `write_audit_entry` fails, agent logs warning but does NOT halt workflow
  - Classification proceeds; audit gap is noted in agent output

## BR-IA-14: Audit Logging Rules

- Every initial classification run MUST produce one audit entry with:
  - `action`: "priority_classification"
  - `details`: summary counts (P1/P2/P3), weights used, thresholds used
- Every reclassification MUST produce one audit entry with:
  - `action`: "priority_reclassification"
  - `details`: order_id, old_priority, new_priority, reason ("planner_override")
- Every re-evaluation triggered by reclassification MUST produce one audit entry with:
  - `action`: "priority_reevaluation"
  - `details`: list of orders whose priority changed, old and new values
- Audit entries use the session_id from the current workflow session

## BR-IA-15: Machine Complexity Scoring

- Machine complexity is derived from `machine_types_required` field on the order
- If order requires both "Rolling Mill" AND "Finishing Line": score = 100
- If order requires only "Rolling Mill": score = 60
- If order requires only "Finishing Line": score = 40
- Unknown or empty machine_types_required: score = 0 (treat as error, log warning)
