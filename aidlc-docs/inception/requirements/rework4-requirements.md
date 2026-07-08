# Rework Cycle 4 — Requirements Document

## Intent Analysis

- **User Request**: Implement two-persona scenario with Ohio and Miami planners, facility dashboards with job tracking and operational efficiency views, notification system for disruption alerts, handshake approval workflow for workload transfers, and capacity agent tuning for realistic utilization rates
- **Request Type**: Enhancement — Major feature additions to existing system
- **Scope**: System-wide — Frontend (new dashboard, notifications, handshake UI), Backend (orchestrator workflow changes, capacity agent tuning), Data (seed data adjustments, Cognito user attributes)
- **Complexity**: Complex — Multiple interacting features across all layers

---

## Functional Requirements

### FR-01: Planner Identity via Cognito User Attributes
Each Cognito user account shall have a custom `plant` attribute (values: `Florida`, `Ohio`) assigned by an admin. The frontend shall read this attribute after authentication and auto-filter all dashboard views, notifications, and chat sessions to the planner's assigned facility. The UI shall display "Miami" for users with `plant=Florida` and "Ohio" for users with `plant=Ohio`.

### FR-02: Dashboard as Default Landing Page
The dashboard shall be the default landing page after login, replacing the current chat-first interface. The chat interface shall be accessible via a tab or collapsible side panel from the dashboard. The dashboard layout shall include:
- Header bar with planner identity (facility name, user name), notification area, and navigation tabs (Dashboard, Chat, Transfer Negotiation)
- Main content area with two switchable views: Job Status Tracking and Operational Efficiency Monitoring

### FR-03: Job Status Tracking View
The Job Status Tracking view shall display production orders for the planner's facility with the following capabilities:

**Active Orders Table** — columns: Order ID, Product Family, Quantity, Due Date, Customer Name, Customer Tier, Status, Machine Types Required, Rolling Mill Hours, Finishing Line Hours, Raw Material Tons. Sortable and filterable by any column.

**Historical Orders** — a toggle or tab to show completed/cancelled orders from the last 30 days with the same columns plus a Completion Date column.

**Summary Cards** — at the top of the view, show quick-glance cards: Total Active Orders, Orders Due This Week, Orders by Status (Active/On Hold/Transferred), Orders by Priority (P1/P2/P3).

### FR-04: Operational Efficiency Monitoring View
The Operational Efficiency Monitoring view shall display facility-level operational metrics:

**Machine Utilization Gauges** — for each machine type (Rolling Mill, Finishing Line), show circular or bar gauges for Normal shift utilization %, Overtime availability %, and Weekend availability %. Color-coded: green (<70%), yellow (70-85%), red (>85%).

**Manpower Allocation** — bar chart showing total operators, currently allocated, and available surplus. Include overtime and weekend shift capacity.

**Material Inventory Levels** — per material type (Hot-Rolled Coil, Steel Slab, Steel Billet), show current inventory, committed to orders, and available surplus in tons. Color-coded by stock level (green = adequate, yellow = low, red = critical).

**Equipment Status** — status indicators per machine: Online, Maintenance, Offline.

**Summary Cards** — overall utilization %, manpower utilization %, total material stock level.

**Historical Trend Charts** — line charts showing utilization %, manpower allocation, and material levels over the last 7 days. Data sourced from periodic snapshots stored in DynamoDB.

### FR-05: Disruption Notification System
When a disruption event is detected (via the orchestrator agent), the system shall display an in-app banner alert at the top of the affected planner's dashboard. The banner shall:
- Persist until the planner explicitly acknowledges/dismisses it
- Display: disruption type, affected facility, timestamp, brief description
- Include an "Acknowledge" button that dismisses the banner and logs the acknowledgment
- Be visible across all dashboard views (Job Status, Efficiency, Chat)
- Only appear for the planner whose facility is affected by the disruption

### FR-06: Handshake Approval Workflow — AI Proposal Phase
After disruption detection and impact assessment, the AI orchestrator shall propose transfer candidates to the Miami (Florida) planner. The proposal shall include:
- List of orders recommended for transfer with priority scores, reasoning, and constraint funnel results
- Each order shows: Order ID, Product Family, Due Date, Customer Tier, Order Value, Transfer Recommendation (transfer / transfer_with_procurement / transfer_overtime / non_transferable)
- Miami planner reviews and confirms which orders to send as transfer requests to Ohio

### FR-07: Handshake Approval Workflow — Ohio Approval Phase
Transfer requests confirmed by Miami planner shall appear in the Ohio planner's dashboard as pending transfer requests. Ohio planner shall:
- See a "Pending Transfers" section/tab showing incoming requests with full order details and AI reasoning
- Approve or decline each transfer request individually with an optional reason field
- Approved transfers update order status to "Transferred" and adjust Ohio capacity accordingly
- Declined transfers trigger a notification to Miami planner

### FR-08: Transfer Decline and Resubmission
When Ohio planner declines a transfer request:
- Miami planner receives a notification with the decline reason
- Miami planner can modify the request (adjust timeline, reduce quantity, change priority) and resubmit
- Resubmitted requests appear as new pending transfers for Ohio planner
- The system tracks the negotiation history (original request → decline → resubmission)

### FR-09: Shared Transfer Negotiation Channel
In addition to independent chat sessions per planner, the system shall provide a shared "Transfer Negotiation" channel/view where:
- Both planners can see transfer request status (proposed, confirmed, pending approval, approved, declined, resubmitted)
- Transfer negotiation messages and decisions are visible to both planners
- This channel is read-only for chat — decisions are made through the approval UI, not free-text

### FR-10: Independent Planner Chat Sessions
Each planner shall have their own independent chat session with the orchestrator agent. The orchestrator shall:
- Scope its responses to the planner's facility context
- Include the planner's plant identity in the session metadata sent to the agent
- Maintain separate AgentCore Memory sessions per planner

### FR-11: Capacity Agent Utilization Tuning
Adjust the Ohio plant seed data and capacity calculation to reflect realistic utilization rates:
- Rolling Mill normal utilization: increase from 75% to 82%
- Finishing Line normal utilization: increase from 65% to 80%
- Increase Ohio orders' committed hours to consume more of the available capacity
- Result: Ohio plant should show moderate surplus (not excessive), making transfer approval decisions more meaningful and realistic

### FR-12: Florida/Miami Plant Seed Data
Add seed data for Florida plant capacity, manpower, and materials so the Miami planner's dashboard shows operational data before any disruption:
- Florida Rolling Mill and Finishing Line capacity data (similar structure to Ohio)
- Florida manpower allocation
- Florida raw material inventory
- This data represents the "normal operating state" before disruption

### FR-13: Post-Workflow Dashboard End State
After the disruption workflow completes (all transfers approved/declined, handshake finalized), both dashboards shall update to reflect the final state:

**Miami (Florida) Planner Dashboard**:
- Job Status Tracking shows all Florida orders with updated statuses: "Transferred" for orders moved to Ohio, "Suspended" or "On Hold" for remaining orders that cannot be produced during the disruption. The active order count drops to zero or near-zero for the impacted facility.
- Operational Efficiency Monitoring shows zeroed-out or minimal utilization (plant offline/disrupted), equipment status set to "Offline", manpower showing "Evacuated" or "Reassigned".

**Ohio Planner Dashboard**:
- Job Status Tracking shows Ohio's original orders plus newly transferred orders from Florida. Transferred orders are visually distinguished (badge, color, or icon). Ohio's own lower-priority orders (P3) are shown with a "De-prioritized" or "Deferred" status to make room for critical transferred work.
- Operational Efficiency Monitoring shows increased utilization reflecting the absorbed workload — machine gauges move into yellow/red zones, manpower allocation increases, material inventory decreases.
- Summary cards update to show: original Ohio orders count, transferred orders count, de-prioritized orders count, new overall utilization %.

This end-state dashboard serves as the demo conclusion, showing the before-and-after impact of the disruption response across both facilities.

---

## Non-Functional Requirements

### NFR-01: Dashboard Load Performance
The dashboard shall load initial data (orders, capacity, materials) within 3 seconds of authentication. Use client-side caching for subsequent navigations between views.

### NFR-02: Real-Time Notification Delivery
Disruption notifications shall appear on the affected planner's dashboard within 5 seconds of the orchestrator detecting the event.

### NFR-03: Security — Planner Data Isolation
Planners shall only see data for their assigned facility. The `plant` attribute from Cognito shall be validated server-side (in the REST proxy or orchestrator) to prevent cross-facility data access.

### NFR-04: Accessibility
Dashboard views shall meet WCAG 2.1 Level AA guidelines for color contrast, keyboard navigation, and screen reader compatibility. Utilization gauges shall include text alternatives.

### NFR-05: Security Baseline Compliance
All changes shall comply with the Security Baseline extension rules (enabled from previous cycles).
