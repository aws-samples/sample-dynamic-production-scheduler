# Domain Entities — Unit 6: Constraint Matching Agent

## Overview

The Constraint Matching Agent processes Florida orders through a 4-layer constraint funnel, presenting one order at a time to the Planner with transfer recommendations. It reads prioritized orders from shared context (Unit 4), capacity snapshot from shared context (Unit 5), and Ohio data from ERP Data MCP. It persists the running capacity tracker to DynamoDB via ERP Data MCP. This document defines the agent's internal data models, configuration, and input/output contracts.

---

## Agent Configuration Schema

```python
@dataclass
class ConstraintMatchingConfig:
    utilization_warning_pct: float       # default 0.90 (90% threshold alert)
    max_cascade_depth: int               # default 5 (multi-level cascade simulation)
    manpower_hard_limit_shift: str       # "Normal" — hard constraint for normal shifts
    manpower_soft_limit_shifts: list[str]  # ["Overtime", "Weekend"] — soft warning only
```

---

## Funnel Layer Result Entities

### Layer 1: Equipment Compatibility

```python
@dataclass
class EquipmentCheckResult:
    passed: bool
    rolling_mill_compatible: bool
    finishing_line_compatible: bool
    gauge_in_range: bool                 # True if order gauge within machine min/max
    gauge_order: float | None            # order's required gauge thickness
    gauge_machine_min: float | None
    gauge_machine_max: float | None
    failure_reason: str | None           # e.g., "Steel Bars not supported by Rolling Mill"
    explanation: str                     # natural language reasoning
```

### Layer 2: Material Availability

```python
@dataclass
class MaterialCheckResult:
    passed: bool
    match_status: str                    # "Full Match" / "Partial Match" / "No Match"
    required_tons: float
    available_surplus_tons: float
    shortfall_tons: float                # 0 if full match
    procurement_lead_time_days: int      # 0 if full match
    production_time_days: float          # estimated production duration
    days_until_due_date: int
    procurement_feasible: bool           # lead_time + production_time <= days_until_due
    failure_reason: str | None           # e.g., "Procurement + production exceeds deadline"
    explanation: str
```

### Layer 3: Machine Utilization

```python
@dataclass
class UtilizationCheckResult:
    passed: bool
    rolling_mill_available_hrs: float
    rolling_mill_required_hrs: float
    finishing_line_available_hrs: float
    finishing_line_required_hrs: float
    recommended_shift_tier: str          # "Normal" / "Overtime" / "Weekend"
    shift_escalation_needed: bool        # True if normal hours insufficient
    escalation_options: list[ShiftEscalationOption]
    utilization_warning: bool            # True if any machine > 90% after transfer
    manpower_sufficient: bool
    manpower_available: int
    manpower_required: int
    manpower_constraint_type: str        # "hard" or "soft" (tiered per shift)
    failure_reason: str | None
    explanation: str

@dataclass
class ShiftEscalationOption:
    shift_tier: str                      # "Overtime" / "Weekend"
    rolling_mill_surplus_hrs: float
    finishing_line_surplus_hrs: float
    manpower_note: str                   # "soft warning — temp workers may be needed"
```

### Layer 4: Cascade Impact

```python
@dataclass
class CascadeImpactResult:
    passed: bool                         # True if no Ohio orders pushed past deadline
    simulation_depth: int                # how many levels of cascade were checked
    impacted_orders: list[CascadeImpactedOrder]
    total_orders_impacted: int
    has_penalty_risk: bool               # True if any impacted order has penalty_clause
    failure_reason: str | None
    explanation: str

@dataclass
class CascadeImpactedOrder:
    order_id: str
    customer_id: str
    customer_tier: str
    original_slack_days: int
    new_slack_days: int                  # negative = past deadline
    days_past_deadline: int              # 0 if still on time
    penalty_clause: bool
    cascade_level: int                   # 1 = direct impact, 2+ = cascading
    impact_explanation: str              # e.g., "Pushed from Day 18 to Day 23, 2 days past deadline"
```

---

## Composite Funnel Result

```python
@dataclass
class FunnelResult:
    order_id: str
    priority: str                        # P1/P2/P3
    layer1_equipment: EquipmentCheckResult
    layer2_material: MaterialCheckResult
    layer3_utilization: UtilizationCheckResult
    layer4_cascade: CascadeImpactResult
    all_layers_passed: bool              # True only if all 4 layers passed
    recommendation: str                  # see OrderRecommendation categories
    recommendation_category: str         # enum value
    recommendation_explanation: str      # natural language summary
    conditions: list[str]                # e.g., ["Requires procurement", "Overtime needed"]
```

---

## Order Recommendation Categories

```python
class RecommendationCategory:
    TRANSFER = "Transfer"                          # all layers pass on normal shift
    TRANSFER_WITH_PROCUREMENT = "Transfer with procurement"  # Layer 2 partial match
    TRANSFER_ON_OVERTIME = "Transfer on overtime"  # Layer 3 needs overtime escalation
    TRANSFER_ON_WEEKEND = "Transfer on weekend"    # Layer 3 needs weekend escalation
    TRANSFER_WITH_CONDITIONS = "Transfer with conditions"  # catch-all: multiple conditions
    NON_TRANSFERABLE = "Non-transferable"           # any layer hard-fails
```

Decision logic:
- If any layer hard-fails → `NON_TRANSFERABLE`
- If Layer 2 = Partial Match AND Layer 3 needs escalation → `TRANSFER_WITH_CONDITIONS`
- If Layer 2 = Partial Match only → `TRANSFER_WITH_PROCUREMENT`
- If Layer 3 needs overtime only → `TRANSFER_ON_OVERTIME`
- If Layer 3 needs weekend only → `TRANSFER_ON_WEEKEND`
- If all layers pass on normal shift → `TRANSFER`

---

## Running Capacity Tracker

```python
@dataclass
class RunningCapacityTracker:
    session_id: str
    last_updated: str                    # ISO timestamp
    rolling_mill_remaining_hrs: RunningShiftHours
    finishing_line_remaining_hrs: RunningShiftHours
    material_remaining_tons: float
    manpower_remaining: int
    orders_processed: list[ProcessedOrderEntry]
    orders_skipped: list[str]            # order_ids in skip queue
    orders_approved: list[str]           # order_ids approved for transfer
    orders_rejected: list[str]           # order_ids marked non-transferable

@dataclass
class RunningShiftHours:
    normal_hrs: float
    overtime_hrs: float
    weekend_hrs: float
    total_hrs: float                     # sum of all tiers

@dataclass
class ProcessedOrderEntry:
    order_id: str
    decision: str                        # "approved" / "rejected" / "skipped"
    recommendation_category: str
    rolling_mill_hrs_consumed: float     # 0 if rejected/skipped
    finishing_line_hrs_consumed: float
    material_tons_consumed: float
    decided_at: str                      # ISO timestamp
```

---

## Planner Decision Entities

```python
@dataclass
class OrderDecision:
    order_id: str
    action: str                          # "approve" / "reject" / "skip"
    decided_at: str                      # ISO timestamp

@dataclass
class OrderDecisionResult:
    order_id: str
    action: str
    recommendation_category: str
    capacity_consumed: CapacityConsumed | None  # None if rejected/skipped
    tracker_updated: bool
    next_order_id: str | None            # None if queue empty
    explanation: str

@dataclass
class CapacityConsumed:
    rolling_mill_hrs: float
    finishing_line_hrs: float
    material_tons: float
    operator_hrs: float
    shift_tier_used: str                 # "Normal" / "Overtime" / "Weekend"
```

---

## Skip Queue Entities

```python
@dataclass
class SkipQueueEntry:
    order_id: str
    priority: str
    skipped_at: str                      # ISO timestamp
    original_position: int               # position in priority queue when skipped
    revisit_requested: bool              # True if planner explicitly asked to revisit

@dataclass
class OrderQueue:
    pending: list[str]                   # order_ids not yet processed (priority order)
    skipped: list[str]                   # order_ids skipped, appended to end
    current_index: int                   # pointer to current order in pending
```

---

## Input Contracts

### From Shared Context — `prioritized_orders` (Unit 4)

```python
@dataclass
class SharedOrderEntry:
    order_id: str
    priority: str                        # P1/P2/P3
    weighted_score: float
    due_date: str
    product_family: str
    quantity: int
    order_value: float
    machine_types_required: list[str]
    customer_id: str
    customer_tier: str
    rolling_mill_hours: float
    finishing_line_hours: float
    raw_material_tons: float
```

### From Shared Context — `capacity_snapshot` (Unit 5)

```python
@dataclass
class SharedCapacitySnapshot:
    session_id: str
    analyzed_at: str
    rerouting_window_days: int
    bottleneck: BottleneckInfo | None
    surplus_summary: SurplusSummary | None
    active_constraints: list[str]
    delays_approved: list[str]
```

### From ERP Data MCP — Equipment, Materials, Orders, Manpower

Same tool contracts as Unit 5 (see Unit 5 domain entities). Key tools consumed:
- `get_machine_capacity(machine_type)` → EquipmentCapability fields
- `get_materials()` → MaterialSurplus fields
- `get_orders(plant="Ohio", status="Active")` → OhioOrderLoad fields
- `get_manpower()` → ManpowerAvailability fields
- `get_running_tracker(session_id)` → RunningCapacityTracker
- `update_running_tracker(session_id, tracker_data)` → Updated tracker

---

## Output Contracts

### Agent Response — Order Presentation

```python
@dataclass
class OrderPresentation:
    order_id: str
    priority: str
    product_family: str
    customer_name: str
    customer_tier: str
    due_date: str
    quantity: int
    order_value: float
    funnel_result: FunnelResult
    recommendation_text: str             # natural language recommendation
    action_prompt: str                   # "Approve / Skip / Reject"
```

### Agent Response — Transfer Summary (after all orders processed)

```python
@dataclass
class TransferSummary:
    total_orders_evaluated: int
    orders_approved: int
    orders_rejected: int
    orders_skipped: int
    capacity_consumed: CapacityConsumed
    capacity_remaining: RunningShiftHours  # per machine
    summary_text: str                    # natural language summary
```

---

## Audit Entry Schema

```python
@dataclass
class ConstraintMatchingAuditEntry:
    session_id: str
    agent: str                           # "constraint_matching_agent"
    action: str                          # see action types below
    timestamp: str                       # ISO timestamp
    details: dict                        # varies by action type
```

### Action Types

- `funnel_evaluation`: One entry per order evaluated through the funnel
  - details: order_id, layer results (pass/fail), recommendation_category
- `order_decision`: One entry per planner decision
  - details: order_id, action (approve/reject/skip), capacity_consumed
- `order_skip`: One entry per skip
  - details: order_id, queue_position, reason
- `order_revisit`: One entry per revisit request
  - details: order_id, new_funnel_result (re-evaluated with current capacity)
- `tracker_update`: One entry per tracker persistence
  - details: orders_approved count, capacity_remaining summary

---

## Entity Relationships

```
ConstraintMatchingConfig
  +-- utilization_warning_pct
  +-- max_cascade_depth
  +-- manpower_hard_limit_shift
  +-- manpower_soft_limit_shifts

SharedOrderEntry (from Unit 4 shared context)
  --> FunnelResult (computed per order)
  |     +-- EquipmentCheckResult (Layer 1)
  |     +-- MaterialCheckResult (Layer 2)
  |     +-- UtilizationCheckResult (Layer 3)
  |     |     +-- ShiftEscalationOption (0..N)
  |     +-- CascadeImpactResult (Layer 4)
  |           +-- CascadeImpactedOrder (0..N)
  --> OrderPresentation (for planner display)
  --> OrderDecision (planner action)
  --> OrderDecisionResult (post-decision)

RunningCapacityTracker (persisted to DynamoDB)
  +-- RunningShiftHours (per machine)
  +-- ProcessedOrderEntry (per order)

OrderQueue
  +-- pending (priority-ordered)
  +-- skipped (end-of-queue + on-demand revisit)
```
