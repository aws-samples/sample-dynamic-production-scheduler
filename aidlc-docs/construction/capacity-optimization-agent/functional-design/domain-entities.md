# Domain Entities — Unit 5: Capacity & Optimization Agent

## Overview

The Capacity & Optimization Agent is a stateless analysis agent. It reads Ohio capacity data from ERP Data MCP, computes surplus across 5 dimensions, identifies delay candidates, and writes a capacity snapshot to AgentCore Memory. This document defines the agent's internal data models, configuration, and input/output contracts.

---

## Agent Configuration Schema

```python
@dataclass
class CapacityAgentConfig:
    rerouting_window_days: int       # default 10 (configurable)
    delay_threshold_days: int        # default 42 (configurable, 6 weeks)
    utilization_warning_pct: float   # default 0.90 (90% threshold alert)
```

---

## Capacity Dimension Entities

### Equipment Capability

```python
@dataclass
class EquipmentCapability:
    machine_type: str                    # "Rolling Mill" or "Finishing Line"
    product_families_supported: list[str]
    total_hours_per_week: float
    planned_downtime_hrs_week: float
    net_available_hours_per_week: float  # total - downtime
    gauge_range_min: float | None        # Rolling Mill only
    gauge_range_max: float | None        # Rolling Mill only
    setup_time_by_family: dict[str, float]
```

### Machine Utilization (Tiered)

```python
@dataclass
class ShiftUtilization:
    shift_type: str              # "Normal" / "Overtime" / "Weekend"
    total_hours: float           # available hours for this shift type
    committed_hours: float       # hours allocated to existing Ohio orders
    surplus_hours: float         # total - committed
    utilization_pct: float       # committed / total * 100

@dataclass
class MachineUtilization:
    machine_type: str            # "Rolling Mill" or "Finishing Line"
    normal: ShiftUtilization
    overtime: ShiftUtilization
    weekend: ShiftUtilization
    total_surplus_hours: float   # sum of all shift surplus
    effective_surplus_hours: float  # tiered: normal first, then OT, then weekend
```

### Manpower Availability

```python
@dataclass
class ManpowerAvailability:
    total_operators: int
    currently_allocated: int
    available_surplus: int
    overtime_hrs_per_shift: float
    weekend_hrs_per_shift: float
    operators_per_rolling_mill: int
    operators_per_finishing_line: int
```

### Raw Material Surplus

```python
@dataclass
class MaterialSurplus:
    material_type: str
    current_inventory_tons: float
    committed_to_orders_tons: float
    available_surplus_tons: float
    procurement_lead_time_days: int
    unit_cost: float
```

### Existing Order Load

```python
@dataclass
class OhioOrderLoad:
    order_id: str
    product_family: str
    customer_id: str
    customer_tier: str
    due_date: str
    quantity: int
    order_value: float
    priority: str | None
    rolling_mill_hours: float
    finishing_line_hours: float
    raw_material_tons: float
    slack_days: int              # due_date - estimated_completion
    penalty_clause: bool
```

---

## Capacity Snapshot (Composite)

```python
@dataclass
class BottleneckInfo:
    machine_type: str            # "Rolling Mill" or "Finishing Line"
    surplus_to_demand_ratio: float  # surplus_hours / demand_hours
    surplus_hours: float
    demand_hours: float          # total Florida P1+P2 demand for this machine
    explanation: str             # natural language

@dataclass
class CapacitySnapshot:
    session_id: str
    analyzed_at: str             # ISO timestamp
    rerouting_window_days: int
    equipment: list[EquipmentCapability]
    utilization: list[MachineUtilization]
    manpower: ManpowerAvailability
    materials: list[MaterialSurplus]
    existing_load: list[OhioOrderLoad]
    bottleneck: BottleneckInfo
    active_constraints: list[str]  # planner-added constraints
    total_surplus_summary: SurplusSummary

@dataclass
class SurplusSummary:
    rolling_mill_normal_hrs: float
    rolling_mill_overtime_hrs: float
    rolling_mill_weekend_hrs: float
    finishing_line_normal_hrs: float
    finishing_line_overtime_hrs: float
    finishing_line_weekend_hrs: float
    total_material_surplus_tons: float
    total_manpower_surplus: int
```

---

## Delay Candidate Entities

```python
@dataclass
class DelayCandidateInfo:
    order_id: str
    product_family: str
    customer_id: str
    customer_tier: str
    due_date: str
    quantity: int
    order_value: float
    priority: str                # must be P3
    slack_days: int
    penalty_clause: bool
    freed_rolling_mill_hours: float
    freed_finishing_line_hours: float
    freed_material_tons: float
    freed_operator_hours: float
    remaining_buffer_days: int   # slack after delay
    risk_level: str              # "Low" / "Medium" / "High"
    trade_off_explanation: str   # natural language

@dataclass
class DelayDecision:
    order_id: str
    approved: bool
    decided_at: str              # ISO timestamp

@dataclass
class DelayResult:
    decisions: list[DelayDecision]
    capacity_before: SurplusSummary
    capacity_after: SurplusSummary
    bottleneck_before: BottleneckInfo
    bottleneck_after: BottleneckInfo
```

---

## Constraint Entities

```python
@dataclass
class PlannerConstraint:
    constraint_text: str         # natural language (e.g., "No weekend shifts")
    constraint_type: str         # "shift_restriction" / "capacity_limit" / "other"
    applied_at: str              # ISO timestamp
    impact_description: str      # what changed

@dataclass
class ConstraintImpact:
    constraint: PlannerConstraint
    capacity_before: SurplusSummary
    capacity_after: SurplusSummary
    bottleneck_before: BottleneckInfo
    bottleneck_after: BottleneckInfo
```

---

## Input Contracts (from ERP Data MCP)

The agent consumes these MCP tool responses:
- `get_machine_capacity(machine_type)` -> EquipmentCapability fields
- `get_manpower()` -> ManpowerAvailability fields
- `get_materials()` -> list of MaterialSurplus fields
- `get_orders(plant="Ohio", status="Active")` -> list of OhioOrderLoad fields
- `get_customers()` -> customer tier and penalty_clause enrichment

---

## Output Contracts

### Shared Context (AgentCore Memory)

Key: `"capacity_snapshot"`

```json
{
  "session_id": "string",
  "analyzed_at": "ISO timestamp",
  "rerouting_window_days": 10,
  "bottleneck": {
    "machine_type": "Rolling Mill",
    "surplus_to_demand_ratio": 0.32,
    "surplus_hours": 45,
    "demand_hours": 140,
    "explanation": "string"
  },
  "surplus_summary": {
    "rolling_mill_normal_hrs": 20,
    "rolling_mill_overtime_hrs": 15,
    "rolling_mill_weekend_hrs": 10,
    "finishing_line_normal_hrs": 80,
    "finishing_line_overtime_hrs": 35,
    "finishing_line_weekend_hrs": 25,
    "total_material_surplus_tons": 150,
    "total_manpower_surplus": 8
  },
  "active_constraints": [],
  "delays_approved": ["PO-2026-015", "PO-2026-018"]
}
```

Consumed by: Constraint Matching Agent (Unit 6) for available capacity during funnel.

---

## Entity Relationships

```
CapacityAgentConfig
  +-- rerouting_window_days
  +-- delay_threshold_days
  +-- utilization_warning_pct

CapacitySnapshot
  +-- EquipmentCapability (2: Rolling Mill, Finishing Line)
  +-- MachineUtilization (2: Rolling Mill, Finishing Line)
  |     +-- ShiftUtilization (3: Normal, Overtime, Weekend)
  +-- ManpowerAvailability
  +-- MaterialSurplus (per material type)
  +-- OhioOrderLoad (existing Ohio orders)
  +-- BottleneckInfo
  +-- SurplusSummary

DelayCandidateInfo (subset of OhioOrderLoad + freed capacity)
  --> DelayDecision (planner approval/rejection)
  --> DelayResult (before/after comparison)

PlannerConstraint --> ConstraintImpact (before/after comparison)
```
