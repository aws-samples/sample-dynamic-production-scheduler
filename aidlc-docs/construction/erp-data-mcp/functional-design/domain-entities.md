# Domain Entities — Unit 1: ERP Data MCP Server

## DynamoDB Table Schemas

### Table 1: production_orders

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| order_id | String | PK | Unique ID (e.g., PO-2026-001) |
| plant | String | GSI-PK | "Florida" or "Ohio" |
| product_family | String | | Steel Sheets / Steel Coils / Steel Plates / Steel Bars |
| quantity | Number | | Quantity in units |
| due_date | String | | ISO date (YYYY-MM-DD) |
| machine_types_required | List[String] | | ["Rolling Mill"], ["Finishing Line"], or ["Rolling Mill", "Finishing Line"] |
| customer_id | String | | Customer reference (e.g., CUST-1001) |
| order_value | Number | | Dollar amount |
| customer_tier | String | | Tier1 / Tier2 / Tier3 |
| priority | String | | P1 / P2 / P3 / null (null = not yet classified) |
| status | String | | Active / Delayed / Transferred / Cancelled |
| rolling_mill_hours | Number | | Estimated Rolling Mill hours needed |
| finishing_line_hours | Number | | Estimated Finishing Line hours needed |
| raw_material_tons | Number | | Raw material required (tons) |
| created_at | String | | ISO timestamp |

**GSI**: `plant-status-index` — PK: `plant`, SK: `status` (enables querying all Florida Active orders)

### Table 2: machine_capacity

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| machine_type | String | PK | "Rolling Mill" or "Finishing Line" |
| plant | String | SK | "Ohio" (only Ohio capacity tracked) |
| product_families_supported | List[String] | | Product families this machine can process |
| total_hours_per_week | Number | | Total available hours/week |
| planned_downtime_hrs_week | Number | | Scheduled maintenance hours/week |
| utilization_pct_normal | Number | | Current utilization % normal shifts |
| availability_pct_overtime | Number | | Availability % overtime shifts |
| availability_pct_weekend | Number | | Availability % weekend shifts |
| setup_time_by_family | Map | | Setup time in hours per product family transition |
| gauge_range_min | Number | | Min gauge (Rolling Mill only, null for Finishing Line) |
| gauge_range_max | Number | | Max gauge (Rolling Mill only, null for Finishing Line) |

### Table 3: manpower

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| plant | String | PK | "Ohio" |
| total_operators | Number | | Total headcount |
| currently_allocated | Number | | Operators on active Ohio orders |
| available_surplus | Number | | Total minus Allocated |
| overtime_hrs_per_shift | Number | | Available overtime hours/shift |
| weekend_hrs_per_shift | Number | | Available weekend hours/shift |
| operators_per_rolling_mill | Number | | Operators needed per Rolling Mill shift |
| operators_per_finishing_line | Number | | Operators needed per Finishing Line shift |

### Table 4: raw_materials

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| material_type | String | PK | Material identifier (e.g., "Hot-Rolled Coil") |
| plant | String | SK | "Ohio" |
| current_inventory_tons | Number | | Total inventory |
| committed_to_orders_tons | Number | | Allocated to active Ohio orders |
| available_surplus_tons | Number | | Current minus Committed |
| procurement_lead_time_days | Number | | Days to procure additional stock |
| unit_cost | Number | | Cost per ton (for reporting) |

### Table 5: customers

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| customer_id | String | PK | Unique ID (e.g., CUST-1001) |
| customer_name | String | | Customer name |
| customer_tier | String | | Tier1 / Tier2 / Tier3 |
| penalty_clause | Boolean | | Whether customer has penalty clause for late delivery |
| contact_email | String | | Contact email (placeholder) |

### Table 6: running_tracker

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| session_id | String | PK | Workflow session ID |
| rolling_mill_normal_hrs | Number | | Remaining Rolling Mill hours (normal shift) |
| rolling_mill_overtime_hrs | Number | | Remaining Rolling Mill hours (overtime) |
| rolling_mill_weekend_hrs | Number | | Remaining Rolling Mill hours (weekend) |
| finishing_line_normal_hrs | Number | | Remaining Finishing Line hours (normal shift) |
| finishing_line_overtime_hrs | Number | | Remaining Finishing Line hours (overtime) |
| finishing_line_weekend_hrs | Number | | Remaining Finishing Line hours (weekend) |
| material_surplus_tons | Map | | Remaining surplus by material type |
| manpower_surplus | Number | | Remaining available operators |
| orders_transferred | List[String] | | Order IDs transferred to Ohio |
| orders_delayed | List[String] | | Ohio order IDs delayed |
| orders_rejected | List[String] | | Order IDs marked non-transferable |
| last_updated | String | | ISO timestamp |

---

## Entity Relationships

```
customers 1---* production_orders (via customer_id)
production_orders *---* machine_capacity (via machine_types_required)
production_orders *---* raw_materials (via product_family -> material mapping)
running_tracker 1---1 session (tracks capacity state for one workflow session)
```

## Product Family to Material Mapping

| Product Family | Primary Material | Rolling Mill Required | Finishing Line Required |
|---------------|-----------------|----------------------|----------------------|
| Steel Sheets | Hot-Rolled Coil | Yes | Yes |
| Steel Coils | Hot-Rolled Coil | Yes | No |
| Steel Plates | Steel Slab | No | Yes |
| Steel Bars | Steel Billet | Yes | Yes |
