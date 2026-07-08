# Domain Entities — Unit 4: Impact Assessment Agent

## Overview

The Impact Assessment Agent is a stateless scoring agent. It does not own persistent storage — it reads from ERP Data MCP, writes priorities back via MCP tools, and publishes results to AgentCore shared context memory. This document defines the agent's internal data models, configuration schema, and input/output contracts.

---

## Agent Configuration Schema

```python
@dataclass
class ImpactAssessmentConfig:
    weights: ScoringWeights
    thresholds: PriorityThresholds

@dataclass
class ScoringWeights:
    urgency: float           # default 0.40
    customer_tier: float     # default 0.25
    order_value: float       # default 0.20
    machine_complexity: float # default 0.15
    # Invariant: sum == 1.0 (tolerance ±0.001)

@dataclass
class PriorityThresholds:
    p1: int   # default 75, score >= p1 => P1
    p2: int   # default 50, score >= p2 and < p1 => P2
    # score < p2 => P3
    # Invariant: p1 > p2 > 0
```

---

## Scoring Model Entities

```python
@dataclass
class CriterionScores:
    urgency: int              # 0-100
    customer_tier: int        # 0-100
    order_value: int          # 0-100
    machine_complexity: int   # 0-100

@dataclass
class ScoredOrder:
    order_id: str
    product_family: str
    customer_id: str
    customer_name: str
    customer_tier: str        # Tier1/Tier2/Tier3
    due_date: str             # YYYY-MM-DD
    quantity: int
    order_value: float
    machine_types_required: list[str]
    scores: CriterionScores
    weighted_score: float     # 0.0 - 100.0
    priority: str             # P1/P2/P3
    manually_classified: bool # true if Planner overrode
    original_priority: str | None  # set only if reclassified
```

---

## Input Contract

### From ERP Data MCP — `get_orders` Response

```python
@dataclass
class OrderInput:
    order_id: str
    plant: str
    product_family: str
    quantity: int
    due_date: str
    machine_types_required: list[str]
    customer_id: str
    order_value: float
    customer_tier: str
    priority: str | None
    status: str
    rolling_mill_hours: float
    finishing_line_hours: float
    raw_material_tons: float
```

### From ERP Data MCP — `get_customers` Response

```python
@dataclass
class CustomerInput:
    customer_id: str
    customer_name: str
    customer_tier: str
    penalty_clause: bool
```

---

## Output Contracts

### Agent Response — Priority Summary (Phase 1)

```python
@dataclass
class PrioritySummary:
    total_orders: int
    p1_count: int
    p2_count: int
    p3_count: int
    p1_total_value: float
    p2_total_value: float
    p3_total_value: float
    primary_driver: str       # e.g., "urgency" or "customer_tier"
    summary_text: str         # natural language summary
```

### Agent Response — Grouped Table (Phase 2)

```python
@dataclass
class OrderTableRow:
    order_id: str
    product_family: str
    customer_name: str
    customer_tier: str
    due_date: str
    quantity: int
    order_value: float
    weighted_score: float

@dataclass
class PriorityGroupTable:
    priority: str             # P1/P2/P3
    orders: list[OrderTableRow]
    subtotal_quantity: int
    subtotal_value: float
```

### Agent Response — Order Explanation (Phase 3)

```python
@dataclass
class OrderExplanation:
    order_id: str
    weighted_score: float
    priority: str
    scores: CriterionScores
    weights_used: ScoringWeights
    explanation_text: str     # natural language breakdown
```

---

## Shared Context Schema (AgentCore Memory)

Written after classification, consumed by Unit 5 and Unit 6.

```python
@dataclass
class SharedPrioritizedOrders:
    session_id: str
    classified_at: str        # ISO timestamp
    weights: ScoringWeights
    thresholds: PriorityThresholds
    summary: PrioritySummary
    orders: list[SharedOrderEntry]

@dataclass
class SharedOrderEntry:
    order_id: str
    priority: str
    weighted_score: float
    scores: CriterionScores
    manually_classified: bool
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

Key: `"prioritized_orders"` in AgentCore Memory.

---

## Reclassification Entities

```python
@dataclass
class ReclassificationRequest:
    order_id: str
    new_priority: str         # P1/P2/P3

@dataclass
class ReclassificationResult:
    overridden_order: ScoredOrder
    reevaluated_orders: list[ScoredOrder]  # orders whose priority changed
    updated_summary: PrioritySummary
```

---

## Audit Entry Schema

```python
@dataclass
class ClassificationAuditEntry:
    session_id: str
    agent: str                # "impact_assessment_agent"
    action: str               # "priority_classification" | "priority_reclassification" | "priority_reevaluation"
    timestamp: str            # ISO timestamp
    details: dict             # varies by action type
```

### Details by Action Type

**priority_classification**:
```json
{
  "total_orders": 20,
  "p1_count": 8,
  "p2_count": 7,
  "p3_count": 5,
  "weights": {"urgency": 0.40, "customer_tier": 0.25, "order_value": 0.20, "machine_complexity": 0.15},
  "thresholds": {"p1": 75, "p2": 50}
}
```

**priority_reclassification**:
```json
{
  "order_id": "PO-2026-003",
  "old_priority": "P2",
  "new_priority": "P1",
  "reason": "planner_override"
}
```

**priority_reevaluation**:
```json
{
  "trigger": "reclassification of PO-2026-003",
  "orders_changed": [
    {"order_id": "PO-2026-008", "old_priority": "P2", "new_priority": "P3"}
  ]
}
```

---

## Entity Relationships

```
ImpactAssessmentConfig
  +-- ScoringWeights
  +-- PriorityThresholds

OrderInput (from ERP Data MCP)
  --> CriterionScores (computed)
  --> ScoredOrder (enriched with scores + priority)

ScoredOrder
  --> SharedOrderEntry (subset written to shared context)
  --> OrderTableRow (subset for presentation)
  --> OrderExplanation (on-demand per order)

ReclassificationRequest
  --> ReclassificationResult
  --> ClassificationAuditEntry
```
