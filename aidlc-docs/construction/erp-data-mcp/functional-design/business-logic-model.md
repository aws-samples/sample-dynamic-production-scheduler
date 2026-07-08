# Business Logic Model — Unit 1: ERP Data MCP Server

## MCP Tool Contracts

### Tool 1: get_orders

**Purpose**: Query production orders by plant and optional status filter

**Input Schema**:
```json
{
  "plant": {
    "type": "string",
    "enum": ["Florida", "Ohio"],
    "required": true,
    "description": "Plant to query orders from"
  },
  "status": {
    "type": "string",
    "enum": ["Active", "Delayed", "Transferred", "Cancelled"],
    "required": false,
    "description": "Optional status filter"
  }
}
```

**Output Schema**:
```json
{
  "orders": [
    {
      "order_id": "string",
      "plant": "string",
      "product_family": "string",
      "quantity": "number",
      "due_date": "string (YYYY-MM-DD)",
      "machine_types_required": ["string"],
      "customer_id": "string",
      "order_value": "number",
      "customer_tier": "string",
      "priority": "string | null",
      "status": "string",
      "rolling_mill_hours": "number",
      "finishing_line_hours": "number",
      "raw_material_tons": "number",
      "created_at": "string (ISO timestamp)"
    }
  ],
  "count": "number"
}
```

**Validation Rules**:
- `plant` must be exactly "Florida" or "Ohio" (case-sensitive)
- If `status` provided, must be valid enum value
- Returns empty array if no matching orders (not an error)

---

### Tool 2: get_order_by_id

**Purpose**: Retrieve single order by ID

**Input Schema**:
```json
{
  "order_id": {
    "type": "string",
    "required": true,
    "pattern": "^PO-\\d{4}-\\d{3}$",
    "description": "Order ID (e.g., PO-2026-001)"
  }
}
```

**Output Schema**:
```json
{
  "order": {
    "order_id": "string",
    "plant": "string",
    "product_family": "string",
    "quantity": "number",
    "due_date": "string",
    "machine_types_required": ["string"],
    "customer_id": "string",
    "order_value": "number",
    "customer_tier": "string",
    "priority": "string | null",
    "status": "string",
    "rolling_mill_hours": "number",
    "finishing_line_hours": "number",
    "raw_material_tons": "number",
    "created_at": "string"
  }
}
```

**Validation Rules**:
- `order_id` must match pattern `PO-YYYY-NNN`
- Returns error if order not found

---

### Tool 3: update_order_priority

**Purpose**: Update priority classification for an order (P1/P2/P3)

**Input Schema**:
```json
{
  "order_id": {
    "type": "string",
    "required": true,
    "pattern": "^PO-\\d{4}-\\d{3}$"
  },
  "priority": {
    "type": "string",
    "enum": ["P1", "P2", "P3"],
    "required": true,
    "description": "Priority classification"
  }
}
```

**Output Schema**:
```json
{
  "success": true,
  "order": {
    "order_id": "string",
    "priority": "string",
    "updated_at": "string"
  }
}
```

**Validation Rules**:
- Order must exist
- Priority must be P1, P2, or P3
- Only Florida orders can have priority updated (Ohio orders retain null)

---

### Tool 4: update_order_status

**Purpose**: Update order status (Active/Delayed/Transferred/Cancelled)

**Input Schema**:
```json
{
  "order_id": {
    "type": "string",
    "required": true,
    "pattern": "^PO-\\d{4}-\\d{3}$"
  },
  "status": {
    "type": "string",
    "enum": ["Active", "Delayed", "Transferred", "Cancelled"],
    "required": true
  }
}
```

**Output Schema**:
```json
{
  "success": true,
  "order": {
    "order_id": "string",
    "status": "string",
    "updated_at": "string"
  }
}
```

**Validation Rules**:
- Order must exist
- Status transitions: Active → Delayed, Active → Transferred, Active → Cancelled
- Delayed → Active allowed (reversal)
- Transferred/Cancelled are terminal states

---

### Tool 5: get_machine_capacity

**Purpose**: Query machine capacity data for Ohio plant

**Input Schema**:
```json
{
  "machine_type": {
    "type": "string",
    "enum": ["Rolling Mill", "Finishing Line"],
    "required": true
  }
}
```

**Output Schema**:
```json
{
  "machine_type": "string",
  "plant": "Ohio",
  "product_families_supported": ["string"],
  "total_hours_per_week": "number",
  "planned_downtime_hrs_week": "number",
  "utilization_pct_normal": "number",
  "availability_pct_overtime": "number",
  "availability_pct_weekend": "number",
  "setup_time_by_family": {
    "Steel Sheets": "number",
    "Steel Coils": "number",
    "Steel Plates": "number",
    "Steel Bars": "number"
  },
  "gauge_range_min": "number | null",
  "gauge_range_max": "number | null"
}
```

**Validation Rules**:
- Only Ohio capacity is tracked (Florida is offline)
- `gauge_range_min/max` only populated for Rolling Mill

---

### Tool 6: get_manpower

**Purpose**: Query Ohio plant manpower availability

**Input Schema**:
```json
{}
```
(No parameters required)

**Output Schema**:
```json
{
  "plant": "Ohio",
  "total_operators": "number",
  "currently_allocated": "number",
  "available_surplus": "number",
  "overtime_hrs_per_shift": "number",
  "weekend_hrs_per_shift": "number",
  "operators_per_rolling_mill": "number",
  "operators_per_finishing_line": "number"
}
```

**Validation Rules**:
- `available_surplus` = `total_operators` - `currently_allocated`
- Values must be non-negative

---

### Tool 7: get_materials

**Purpose**: Query raw material inventory at Ohio plant

**Input Schema**:
```json
{
  "material_type": {
    "type": "string",
    "enum": ["Hot-Rolled Coil", "Steel Slab", "Steel Billet"],
    "required": false,
    "description": "Optional filter by material type"
  }
}
```

**Output Schema**:
```json
{
  "materials": [
    {
      "material_type": "string",
      "plant": "Ohio",
      "current_inventory_tons": "number",
      "committed_to_orders_tons": "number",
      "available_surplus_tons": "number",
      "procurement_lead_time_days": "number",
      "unit_cost": "number"
    }
  ]
}
```

**Validation Rules**:
- `available_surplus_tons` = `current_inventory_tons` - `committed_to_orders_tons`
- If `material_type` provided, returns single-item array
- Returns all materials if no filter

---

### Tool 8: get_customers

**Purpose**: Query customer data

**Input Schema**:
```json
{
  "customer_id": {
    "type": "string",
    "pattern": "^CUST-\\d{4}$",
    "required": false,
    "description": "Optional customer ID filter"
  }
}
```

**Output Schema**:
```json
{
  "customers": [
    {
      "customer_id": "string",
      "customer_name": "string",
      "customer_tier": "string",
      "penalty_clause": "boolean",
      "contact_email": "string"
    }
  ]
}
```

**Validation Rules**:
- If `customer_id` provided, returns single-item array or error if not found
- Returns all customers if no filter

---

### Tool 9: get_running_tracker

**Purpose**: Get current running capacity tracker for a workflow session

**Input Schema**:
```json
{
  "session_id": {
    "type": "string",
    "required": true,
    "description": "Workflow session ID"
  }
}
```

**Output Schema**:
```json
{
  "session_id": "string",
  "rolling_mill_normal_hrs": "number",
  "rolling_mill_overtime_hrs": "number",
  "rolling_mill_weekend_hrs": "number",
  "finishing_line_normal_hrs": "number",
  "finishing_line_overtime_hrs": "number",
  "finishing_line_weekend_hrs": "number",
  "material_surplus_tons": {
    "Hot-Rolled Coil": "number",
    "Steel Slab": "number",
    "Steel Billet": "number"
  },
  "manpower_surplus": "number",
  "orders_transferred": ["string"],
  "orders_delayed": ["string"],
  "orders_rejected": ["string"],
  "last_updated": "string"
}
```

**Validation Rules**:
- Returns error if session_id not found
- All hour values must be non-negative
- `orders_transferred/delayed/rejected` are order ID arrays

---

### Tool 10: update_running_tracker

**Purpose**: Update running capacity tracker after a decision

**Input Schema**:
```json
{
  "session_id": {
    "type": "string",
    "required": true
  },
  "tracker_data": {
    "type": "object",
    "required": true,
    "properties": {
      "rolling_mill_normal_hrs": "number (optional)",
      "rolling_mill_overtime_hrs": "number (optional)",
      "rolling_mill_weekend_hrs": "number (optional)",
      "finishing_line_normal_hrs": "number (optional)",
      "finishing_line_overtime_hrs": "number (optional)",
      "finishing_line_weekend_hrs": "number (optional)",
      "material_surplus_tons": "object (optional)",
      "manpower_surplus": "number (optional)",
      "add_transferred": "string (optional, order_id to add)",
      "add_delayed": "string (optional, order_id to add)",
      "add_rejected": "string (optional, order_id to add)"
    }
  }
}
```

**Output Schema**:
```json
{
  "success": true,
  "session_id": "string",
  "last_updated": "string"
}
```

**Validation Rules**:
- Session must exist (create if not exists)
- Partial updates allowed (only provided fields updated)
- Hour values cannot go negative (error if update would result in negative)
- `add_transferred/delayed/rejected` appends to respective arrays

---

## Seed Data Structure

### Florida Orders (20 orders)

**Distribution**:
- 8 orders with due dates within 7 days (urgent)
- 7 orders with due dates 8-14 days
- 5 orders with due dates 15-30 days

**Customer Tier Distribution**:
- 6 Tier1 customers (highest priority)
- 8 Tier2 customers
- 6 Tier3 customers

**Product Family Distribution**:
- 5 Steel Sheets (requires Rolling Mill + Finishing Line)
- 5 Steel Coils (requires Rolling Mill only)
- 5 Steel Plates (requires Finishing Line only)
- 5 Steel Bars (requires Rolling Mill + Finishing Line)

**Edge Cases Included**:
1. **Equipment Incompatibility**: 2 orders with product families NOT supported by Ohio Rolling Mill
2. **Partial Material Match**: 3 orders where surplus < required but procurement + production <= deadline
3. **Cascade Impact**: 2 orders that would push Ohio orders past deadline if transferred
4. **High-Value Tier3**: 1 Tier3 order with very high value (tests priority algorithm)
5. **Same-Day Due Date**: 2 orders with identical due dates (tests tiebreaker)

### Ohio Orders (20 orders)

**Distribution**:
- 5 orders with deadline > 6 weeks (delay candidates)
- 10 orders with deadline 2-6 weeks
- 5 orders with deadline < 2 weeks (cannot delay)

**Slack Distribution**:
- 3 orders with negative slack (already at risk)
- 7 orders with slack < 1 week
- 10 orders with slack > 1 week

**Edge Cases Included**:
1. **P3 Delay Candidates**: 5 orders with P3 priority and deadline > 6 weeks
2. **Penalty Clause Orders**: 3 orders with customers having penalty clauses
3. **Near-Capacity Orders**: 2 orders consuming >50% of remaining capacity

### Ohio Capacity Data

**Rolling Mill**:
- Total hours/week: 168 (24x7)
- Planned downtime: 8 hrs/week
- Normal shift utilization: 75%
- Overtime availability: 20%
- Weekend availability: 15%
- Product families supported: Steel Sheets, Steel Coils, Steel Bars
- NOT supported: Steel Plates (equipment incompatibility edge case)

**Finishing Line**:
- Total hours/week: 168
- Planned downtime: 4 hrs/week
- Normal shift utilization: 65%
- Overtime availability: 25%
- Weekend availability: 20%
- Product families supported: Steel Sheets, Steel Plates, Steel Bars
- NOT supported: Steel Coils (only needs Rolling Mill)

### Manpower Data

- Total operators: 45
- Currently allocated: 38
- Available surplus: 7
- Operators per Rolling Mill shift: 4
- Operators per Finishing Line shift: 3
- Overtime hours/shift: 4
- Weekend hours/shift: 8

### Raw Material Data

| Material | Inventory | Committed | Surplus | Lead Time |
|----------|-----------|-----------|---------|-----------|
| Hot-Rolled Coil | 500 tons | 350 tons | 150 tons | 5 days |
| Steel Slab | 300 tons | 280 tons | 20 tons | 7 days |
| Steel Billet | 200 tons | 120 tons | 80 tons | 4 days |

**Edge Cases**:
- Steel Slab has very low surplus (20 tons) — triggers partial match scenarios
- Hot-Rolled Coil has moderate surplus — some orders fit, some don't

### Customer Data

| Customer ID | Name | Tier | Penalty Clause |
|-------------|------|------|----------------|
| CUST-1001 | Acme Manufacturing | Tier1 | Yes |
| CUST-1002 | BuildRight Corp | Tier1 | Yes |
| CUST-1003 | SteelWorks Inc | Tier1 | No |
| CUST-1004 | Metro Construction | Tier2 | Yes |
| CUST-1005 | Harbor Industries | Tier2 | No |
| CUST-1006 | Valley Fabrication | Tier2 | No |
| CUST-1007 | Summit Steel | Tier2 | No |
| CUST-1008 | Coastal Builders | Tier3 | No |
| CUST-1009 | Midwest Metals | Tier3 | No |
| CUST-1010 | Pacific Steel | Tier3 | No |

