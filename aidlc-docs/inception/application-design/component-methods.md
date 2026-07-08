# Component Methods — DisruptionAI

## Agent Layer Methods

### Orchestrator Agent

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `handle_message(message, session_id)` | Process Planner message and route to appropriate handler | User message text, session ID | Agent response (streamed) |
| `start_disruption_workflow(event_data)` | Initiate disruption response after Planner confirms alert | Weather event data | Workflow session ID |
| `execute_round_1()` | Fire Impact Assessment and Capacity & Optimization agents in parallel | None (reads from session) | Shared context populated |
| `execute_round_2()` | Sequence Capacity & Optimization Agent (delays) then Constraint Matching Agent (funnel) | None (reads shared context) | Order-by-order decisions |
| `handle_what_if(question, session_id)` | Route what-if question to affected agents | What-if question text | Recalculated results |
| `generate_summary(decisions)` | Generate plain-language summary of workflow outcome | List of decisions | Summary text |
| `write_audit_entry(entry)` | Write decision to audit trail via Audit MCP | Audit entry object | Success/failure |

### Impact Assessment Agent

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `analyze_florida_orders()` | Query and prioritize all Florida open orders | None | Prioritized order list with P1/P2/P3 |
| `apply_priority_algorithm(orders)` | Apply weighted scoring to classify orders | List of orders | Orders with priority tags |
| `explain_classification(order_id)` | Generate natural language explanation for priority | Order ID | Explanation text |
| `reclassify_order(order_id, new_priority)` | Handle Planner override of priority | Order ID, new priority | Updated order, acknowledgment |
| `get_priority_summary()` | Return distribution summary (e.g., "8 P1, 7 P2, 5 P3") | None | Summary text |

### Capacity & Optimization Agent

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `analyze_ohio_capacity()` | Comprehensive capacity analysis across all 5 dimensions | None | Capacity snapshot object |
| `get_equipment_capability()` | Query Rolling Mill and Finishing Line capabilities | None | Equipment data |
| `get_machine_utilization(shift_type)` | Query utilization by shift type | Shift type (Normal/OT/Weekend) | Utilization percentages |
| `get_manpower_availability()` | Query operator headcount and availability | None | Manpower data |
| `get_material_surplus()` | Query raw material inventory and surplus | None | Material inventory data |
| `get_existing_load()` | Query existing Ohio orders with slack calculations | None | Order load with slack |
| `identify_bottleneck()` | Determine primary constraint (Rolling Mill vs Finishing Line) | Capacity snapshot | Bottleneck identification |
| `apply_constraint(constraint_text)` | Apply Planner constraint and recalculate | Constraint description | Updated capacity snapshot |
| `identify_delay_candidates()` | Find Ohio orders eligible for delay (P3, deadline > 6 weeks) | None | List of delay candidates |
| `calculate_freed_capacity(order_id)` | Calculate capacity freed by delaying an order | Order ID | Freed capacity breakdown |
| `process_delay_decision(order_id, approved)` | Handle Planner approval/rejection of delay | Order ID, decision | Updated state |
| `recalculate_post_delays(approved_delays)` | Recalculate capacity after all approved Ohio delays | List of delayed order IDs | Updated capacity snapshot |

### Constraint Matching Agent

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `run_constraint_funnel(order)` | Run 4-layer constraint check for a Florida order | Order object | Funnel results (pass/fail per layer) |
| `check_equipment_compatibility(order)` | Layer 1: Check if Ohio machines can handle product family | Order object | Pass/fail with reasoning |
| `check_material_availability(order)` | Layer 2: Check raw material (Full/Partial/No match) | Order object | Match status with lead time |
| `check_machine_utilization(order)` | Layer 3: Check available hours, threshold alerts, shift escalation | Order object | Availability status |
| `check_cascade_impact(order)` | Layer 4: Simulate schedule, check for Ohio order deadline violations | Order object | Impact assessment |
| `present_order_recommendation(order, funnel_results)` | Generate recommendation for Planner | Order, funnel results | Recommendation text |
| `process_order_decision(order_id, decision)` | Handle Planner approve/skip/reject | Order ID, decision | Updated running tracker |
| `update_running_tracker(order_id, decision)` | Update capacity tracker after decision | Order ID, decision | Updated tracker state |

---

## MCP Server Tools

### ERP Data MCP Server

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| `get_orders` | Query production orders | `plant` (Florida/Ohio), `status` (optional) | List of order objects |
| `get_order_by_id` | Get single order details | `order_id` | Order object |
| `update_order_priority` | Update order priority classification | `order_id`, `priority` (P1/P2/P3) | Updated order |
| `update_order_status` | Update order status | `order_id`, `status` | Updated order |
| `get_machine_capacity` | Query machine capacity data | `machine_type` (Rolling Mill/Finishing Line) | Capacity object |
| `get_manpower` | Query manpower data | None | Manpower object |
| `get_materials` | Query raw material inventory | `material_type` (optional) | List of material objects |
| `get_customers` | Query customer data | `customer_id` (optional) | Customer object(s) |
| `get_running_tracker` | Get current running capacity tracker | `session_id` | Tracker object |
| `update_running_tracker` | Update running capacity tracker | `session_id`, `tracker_data` | Updated tracker |

### Weather MCP Server

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| `get_active_events` | Query active weather events | `region` (optional) | List of event objects |
| `get_plant_impact` | Check if event impacts a plant | `event_id`, `plant_id` | Impact assessment |

### Audit MCP Server

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| `write_audit_entry` | Write decision to audit trail | `session_id`, `agent`, `action`, `details`, `timestamp` | Entry ID |
| `get_audit_trail` | Read audit entries | `session_id`, `agent` (optional), `start_time` (optional) | List of entries |

---

## Backend Service Methods

### WebSocket Handler

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `on_connect(websocket)` | Handle new WebSocket connection | WebSocket object | Connection ID |
| `on_disconnect(connection_id)` | Handle WebSocket disconnect | Connection ID | None |
| `on_message(connection_id, message)` | Route incoming message to Orchestrator | Connection ID, message | None (async) |
| `stream_response(connection_id, tokens)` | Stream agent response tokens to frontend | Connection ID, token generator | None |
| `send_structured_data(connection_id, data)` | Send structured data (tables, tracker) | Connection ID, data object | None |

### Session Manager

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `create_session()` | Create new workflow session | None | Session ID |
| `get_session(session_id)` | Retrieve session state | Session ID | Session object |
| `write_shared_context(session_id, key, value)` | Write to AgentCore Memory | Session ID, key, value | Success/failure |
| `read_shared_context(session_id, key)` | Read from AgentCore Memory | Session ID, key | Value |
| `checkpoint_session(session_id)` | Persist session state for recovery | Session ID | Success/failure |

---

## Frontend Component Methods

### Chat Interface Component

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `sendMessage(text)` | Send Planner message via WebSocket | Message text | None |
| `handleStreamToken(token)` | Append streaming token to current message | Token string | Updated display |
| `renderStructuredData(data)` | Render table or capacity summary inline | Data object | JSX element |
| `renderAgentBadge(agentName)` | Display which agent is active | Agent name | JSX element |
| `toggleExplanation(messageId)` | Expand/collapse reasoning section | Message ID | Updated display |

### Side Panel Component

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `handleApprove(orderId)` | Send approval decision | Order ID | None |
| `handleReject(orderId)` | Send rejection decision | Order ID | None |
| `handleSkip(orderId)` | Send skip decision | Order ID | None |
| `updateCapacityTracker(trackerData)` | Update tracker display | Tracker object | Updated display |
| `renderAuditTrail(entries)` | Display audit entries | List of entries | JSX element |
| `renderPhaseProgress(currentPhase)` | Show workflow progress | Phase identifier | JSX element |
