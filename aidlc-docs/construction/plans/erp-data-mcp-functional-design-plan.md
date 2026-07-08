# Functional Design Plan — Unit 1: ERP Data MCP Server

## Context
- **Unit**: ERP Data MCP Server
- **Type**: Data Access / MCP Server (Python)
- **Purpose**: Standardized access to mock ERP data in DynamoDB
- **Tools**: 10 MCP tools (get_orders, get_order_by_id, update_order_priority, update_order_status, get_machine_capacity, get_manpower, get_materials, get_customers, get_running_tracker, update_running_tracker)
- **Stories Supported**: US-02, US-03, US-04, US-06, US-07, US-08, US-09

---

## Functional Design Questions

### Question 1: Mock Data Volume
How many mock production orders should be seeded for each plant?

A) Minimal — 10 Florida + 10 Ohio orders (quick to develop, limited edge cases)
B) Standard — 20 Florida + 20 Ohio orders (matches requirements, good edge case coverage)
C) Large — 50+ per plant (stress testing, more realistic)
X) Other (please describe after [Answer]: tag below)

[Answer]: standard

### Question 2: Running Tracker Granularity
What level of detail should the running capacity tracker store?

A) Summary only — Total remaining hours per machine type (Rolling Mill, Finishing Line)
B) Detailed — Remaining hours per machine type per shift type (Normal, Overtime, Weekend) plus material surplus and manpower
C) Full — Detailed plus per-order allocation history (which orders consumed which capacity)
X) Other (please describe after [Answer]: tag below)

[Answer]: detailed

### Question 3: Seed Data Edge Cases
Which edge cases should be included in the mock seed data?

A) Minimal — Basic orders with varying due dates and customer tiers
B) Comprehensive — Include all edge cases from requirements: equipment incompatibility (product family not supported by Ohio), partial raw material matches, cascade impact scenarios, orders requiring both machines, orders requiring only one machine
C) Comprehensive + stress — All of B plus near-capacity scenarios, same-day due dates, zero-surplus materials
X) Other (please describe after [Answer]: tag below)

[Answer]: comprehensive

---

## Execution Steps

- [x] Step 1: Design DynamoDB table schemas (production_orders, machine_capacity, manpower, raw_materials, customers, running_tracker)
- [x] Step 2: Define MCP tool input/output contracts with validation rules
- [x] Step 3: Design seed data structure with edge cases
- [x] Step 4: Define domain entities and data relationships (MERGED into Step 1)
- [x] Step 5: Define business rules (validation, constraints, error handling)
