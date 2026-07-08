# Business Logic Model — Unit 4: Impact Assessment Agent

## Overview

The Impact Assessment Agent evaluates all Florida open production orders and assigns P1/P2/P3 priority classifications using a configurable weighted scoring algorithm. It is invoked by the Orchestrator Agent as a tool call during Round 1 (parallel with Capacity & Optimization Agent).

---

## Priority Scoring Algorithm

### Step 1: Fetch Input Data

Agent calls ERP Data MCP tools:
- `get_orders(plant="Florida", status="Active")` → all active Florida orders
- `get_customers()` → customer tier data for enrichment

### Step 2: Normalize Criteria (0-100 scale)

Each order is scored on 4 criteria, each normalized to a 0-100 scale:

#### Criterion 1: Days-to-Due-Date (Urgency)
```
days_remaining = (due_date - today).days
if days_remaining <= 0:   score = 100  (overdue)
elif days_remaining <= 3:  score = 95
elif days_remaining <= 7:  score = 80
elif days_remaining <= 14: score = 50
elif days_remaining <= 21: score = 30
elif days_remaining <= 30: score = 15
else:                      score = 5
```

#### Criterion 2: Customer Tier
```
Tier1: score = 100
Tier2: score = 60
Tier3: score = 25
```

#### Criterion 3: Order Value
```
Normalize across the order set using min-max scaling:
score = ((order_value - min_value) / (max_value - min_value)) * 100
```
If all orders have the same value, score = 50 for all.

#### Criterion 4: Machine Complexity
```
Requires both Rolling Mill + Finishing Line: score = 100
Requires only Rolling Mill:                  score = 60
Requires only Finishing Line:                score = 40
```
Rationale: orders needing both machines are harder to place, so they get higher urgency.

### Step 3: Apply Configurable Weights

Default weights (urgency-heavy):
```
WEIGHT_URGENCY          = 0.40
WEIGHT_CUSTOMER_TIER    = 0.25
WEIGHT_ORDER_VALUE      = 0.20
WEIGHT_MACHINE_COMPLEXITY = 0.15
```

Weighted score per order:
```
weighted_score = (urgency_score * WEIGHT_URGENCY)
              + (tier_score * WEIGHT_CUSTOMER_TIER)
              + (value_score * WEIGHT_ORDER_VALUE)
              + (complexity_score * WEIGHT_MACHINE_COMPLEXITY)
```

Result: a score between 0 and 100 for each order.

Weights are stored in agent configuration and can be overridden at runtime by the Planner via the Orchestrator (what-if: "What if we prioritize customer tier over urgency?").

### Step 4: Classify P1/P2/P3

Default thresholds (configurable):
```
P1_THRESHOLD = 75   (score >= 75 = P1: Must Move)
P2_THRESHOLD = 50   (score >= 50 and < 75 = P2: Move if Capacity Allows)
                     (score < 50 = P3: Defer with Customer Notification)
```

Thresholds are configurable — Planner can adjust via Orchestrator (e.g., "Lower the P1 threshold to 65").

### Step 5: Sort and Output

Orders are sorted by:
1. Priority group (P1 first, then P2, then P3)
2. Within each group: descending by weighted_score
3. Tiebreaker: ascending by due_date (earlier due date first)

---

## Reclassification Logic (US-03)

When the Planner overrides an order's priority:

### Step 1: Apply Override
- Set the order's priority to the Planner-specified value
- Mark the order as `manually_classified = true`
- Record original priority and new priority for audit

### Step 2: Re-evaluate Affected Orders
- Re-run classification ONLY on orders that were NOT manually classified
- Manually classified orders are pinned — their priority does not change
- This handles cascading effects (e.g., moving a P2 to P1 may shift borderline P2s to P3)

### Step 3: Persist and Notify
- Update order priorities via `update_order_priority` MCP tool
- Write reclassification to audit trail via Audit MCP
- Present updated priority distribution summary to Planner

---

## Agent Presentation Logic (US-02)

### Output Format: Summary First

#### Phase 1: Priority Distribution Summary
Agent presents a natural language summary:
```
"I've analyzed 20 Florida orders. Here's the priority breakdown:
- P1 (Must Move): 8 orders — $2.4M total value
- P2 (Move if Capacity): 7 orders — $1.1M total value
- P3 (Defer): 5 orders — $0.4M total value

The primary driver is urgency: 6 of the 8 P1 orders have due dates within 5 days.
Shall I show the detailed breakdown by priority group?"
```

#### Phase 2: Grouped Tables (on request)
When Planner asks for details, agent presents grouped tables:

P1 Orders Table:
| Order ID | Product Family | Customer | Tier | Due Date | Qty | Value | Score |
|----------|---------------|----------|------|----------|-----|-------|-------|

P2 Orders Table: (same columns)
P3 Orders Table: (same columns)

Each table includes subtotals for quantity and value.

#### Phase 3: Explanation (on request)
For any specific order, agent explains classification logic:
```
"Order PO-2026-003 scored 82/100 (P1):
- Urgency: 95/100 (due in 2 days)
- Customer Tier: 100/100 (Tier1 — Acme Manufacturing)
- Order Value: 65/100 ($180K — above median)
- Machine Complexity: 100/100 (needs both Rolling Mill + Finishing Line)
Weighted: 0.40*95 + 0.25*100 + 0.20*65 + 0.15*100 = 91.0"
```

---

## Agent Tool Bindings

The Impact Assessment Agent uses these MCP tools:

| MCP Server | Tool | Purpose |
|------------|------|---------|
| ERP Data MCP | `get_orders` | Fetch Florida active orders |
| ERP Data MCP | `get_customers` | Fetch customer tier data |
| ERP Data MCP | `update_order_priority` | Persist P1/P2/P3 classification |
| Audit MCP | `write_audit_entry` | Log classification and reclassification decisions |

---

## Shared Context Output

After classification, the agent writes to AgentCore Memory:

```json
{
  "key": "prioritized_orders",
  "value": {
    "session_id": "string",
    "classified_at": "ISO timestamp",
    "weights": {
      "urgency": 0.40,
      "customer_tier": 0.25,
      "order_value": 0.20,
      "machine_complexity": 0.15
    },
    "thresholds": {
      "p1": 75,
      "p2": 50
    },
    "summary": {
      "total_orders": 20,
      "p1_count": 8,
      "p2_count": 7,
      "p3_count": 5,
      "p1_total_value": 2400000,
      "p2_total_value": 1100000,
      "p3_total_value": 400000
    },
    "orders": [
      {
        "order_id": "PO-2026-001",
        "priority": "P1",
        "weighted_score": 91.0,
        "scores": {
          "urgency": 95,
          "customer_tier": 100,
          "order_value": 65,
          "machine_complexity": 100
        },
        "manually_classified": false
      }
    ]
  }
}
```

This shared context is consumed by:
- Capacity & Optimization Agent (Unit 5) — to identify delay candidates
- Constraint Matching Agent (Unit 6) — to process orders in priority order
