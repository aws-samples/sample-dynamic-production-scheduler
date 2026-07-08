# Requirements Document — Rework 7: Transfer Negotiation, Live Capacity Impact & Cross-Plant Dashboard Updates

## Intent Analysis Summary

- **User Request**: After reroute decisions in the constraint funnel, approved orders auto-flow to Transfer Negotiation as "Submitted for Review." Receiving plant reviews/accepts/rejects. Both plants' dashboards update. Bidirectional. Live capacity impact panel during delay optimization and constraint funnel. Final state summary with receiving plant utilization.
- **Request Type**: Enhancement — Major feature additions across frontend and backend
- **Scope Estimate**: Multiple components — Frontend (Transfer Negotiation rework, new CapacityImpactPanel, disruption stepper extension, dashboard updates), Backend (orchestrator update_ui extension, WebSocket push for cross-plant updates), Store (new transfer lifecycle state, capacity impact tracking)
- **Complexity Estimate**: Complex — cross-plant real-time coordination, new three-column layout, bidirectional role logic, WebSocket-driven dashboard sync

---

## Functional Requirements

### FR-01: Auto-Flow from Constraint Funnel to Transfer Negotiation
When the constraint funnel phase completes and orders have been approved for reroute, all funnel-approved orders shall automatically appear in the Transfer Negotiation view with status "Submitted for Review." No additional action from the disrupted plant's planner is required. The transfer requests shall include: order ID, product family, customer name, customer tier, order value, due date, priority classification, constraint funnel results (4-layer pass/fail), and the AI recommendation/reasoning.

### FR-02: Receiving Plant — Incoming Transfer Review Section
The Transfer Negotiation view shall display a dedicated "Incoming Transfers" section/sub-tab for the receiving plant's planner. This section shall:
- Show all orders with status "Submitted for Review" that are destined for the receiving plant
- Display each order as a card or row with: Order ID, Product Family, Customer Name, Customer Tier, Order Value, Due Date, Priority, AI Reasoning
- Provide Accept and Reject buttons per order
- Include an optional free-text reason field (shown on reject, optional on accept)
- Show a header label: "Review these orders to include in your production schedule"

### FR-03: Transfer Accept/Reject Processing
When the receiving plant planner accepts a transfer:
- Order status updates to "Transferred" in the sending plant's context
- Order appears in the receiving plant's Job Status view as a new active order with a "Transferred In" visual badge
- Receiving plant's capacity/utilization metrics update to reflect the absorbed workload

When the receiving plant planner rejects a transfer:
- Order status updates to "Transfer Declined" in the Transfer Negotiation view
- The optional decline reason is stored and visible to both planners
- A notification is sent to the sending plant's planner indicating the decline

### FR-04: Cross-Plant Dashboard Updates (Job Status)
After the receiving plant accepts or rejects transfers:
- **Sending plant's Job Status view**: Transferred orders show status "Transferred to [Receiving Plant]." Remaining orders show "Suspended" or "On Hold" as appropriate.
- **Receiving plant's Job Status view**: Accepted transferred orders appear in the active orders list with a "Transferred In" badge/icon distinguishing them from native orders. The receiving plant's own deferred/de-prioritized orders (P3 delays) show "Deferred" status.

### FR-05: Cross-Plant Dashboard Updates (Operational Efficiency)
After transfer acceptance:
- **Sending plant's Operational Efficiency view**: Utilization gauges reflect reduced/zeroed capacity (plant disrupted). Equipment status shows "Offline."
- **Receiving plant's Operational Efficiency view**: Machine utilization gauges increase to reflect absorbed workload. Manpower allocation increases. Material inventory decreases. Summary cards update with: original orders count, transferred-in orders count, deferred orders count, new overall utilization %.

### FR-06: Summary Notification to Both Planners
After all transfer decisions are finalized (all orders accepted or rejected), both planners receive a summary notification containing:
- Total orders transferred, total orders declined
- Net capacity impact on the receiving plant
- Key decisions summary

### FR-07: Live Capacity Impact Panel — Layout
During the delay optimization and constraint funnel phases of the disruption workflow, the UI shall display a three-column layout:
- **Left**: Navigation/stepper (existing)
- **Center**: Main disruption content (delay cards or funnel cards — existing)
- **Right**: Live Capacity Impact Panel (new)

The right-side panel shall be visible throughout both phases and shall not replace the existing side panel for non-disruption views.

### FR-08: Live Capacity Impact Panel — Content
The Live Capacity Impact Panel shall display:

**Cumulative Running State (Gauges)**:
- Sending plant: Rolling Mill utilization %, Finishing Line utilization %, overall utilization %
- Receiving plant: Rolling Mill utilization %, Finishing Line utilization %, overall utilization %
- Gauges update in real-time after each delay approval or funnel decision
- Color-coded: green (<70%), yellow (70-85%), red (>85%)

**Per-Decision Delta Preview**:
- When a delay candidate or funnel order is being evaluated (before the user decides), show a before/after comparison for the current pending decision
- Format: "If you approve this: Rolling Mill +X hrs (+Y%), Finishing Line +X hrs (+Y%)"
- Clears after the user makes a decision and the next candidate loads

### FR-09: Live Capacity Impact Panel — Data Source (Hybrid)
- Agents emit baseline capacity snapshots via the existing `update_ui` tool (a new `capacityImpact` field containing both plants' current utilization percentages and absolute hours)
- The frontend calculates per-decision deltas locally using the baseline snapshot plus the pending decision's freed/consumed hours from the approval request data
- After each decision, the agent emits an updated baseline reflecting the new cumulative state

### FR-10: Disruption Stepper — Final State Summary Phase
A new final step shall be added to the disruption workflow stepper after the existing Summary phase: "Capacity Summary." This step shall display:
- Receiving plant's final capacity utilization across all dimensions (Rolling Mill, Finishing Line, Manpower, Raw Material)
- Before vs. after comparison (pre-disruption baseline vs. post-all-decisions)
- Visual gauges matching the Operational Efficiency view style
- Count of: orders absorbed, orders deferred, total capacity consumed
- A "Return to Dashboard" button that navigates to the receiving plant's dashboard

### FR-11: Bidirectional Support — Dynamic Role Swap
The system shall support disruptions at either plant with automatic role assignment:
- The plant selected during disruption initiation is the "sender" (disrupted plant)
- The other plant is automatically the "receiver"
- All UI labels adapt: "Incoming Transfers" shows on the receiver's Transfer Negotiation tab, "Outgoing Transfers" shows on the sender's tab
- Capacity impact panel labels adapt: sender plant shows decreasing utilization, receiver plant shows increasing utilization
- Transfer Negotiation flow, dashboard updates, and notifications all use sender/receiver roles rather than hardcoded plant names
- Works for Florida disruption → Ohio receives AND Ohio disruption → Florida receives

### FR-12: `update_ui` Tool Extension — `capacityImpact` Field
The orchestrator's `update_ui` Pydantic schema shall be extended with a new optional field:
```
capacityImpact: {
  senderPlant: { name, rollingMill: {current%, projected%}, finishingLine: {current%, projected%}, overall: {current%, projected%} },
  receiverPlant: { name, rollingMill: {current%, projected%}, finishingLine: {current%, projected%}, overall: {current%, projected%} }
}
```
The orchestrator shall call `update_ui` with `capacityImpact` data:
- At the start of delay optimization (baseline snapshot)
- After each delay decision (updated cumulative state)
- At the start of constraint funnel (post-delay baseline)
- After each funnel decision (updated cumulative state)

### FR-13: `update_ui` Tool Extension — `transferOrders` Field
The orchestrator's `update_ui` schema shall include a new optional field:
```
transferOrders: [{ orderId, product, customer, customerTier, value, dueDate, priority, recommendation, reasoning, funnelResults: {equipment, material, utilization, cascade} }]
```
Emitted when the constraint funnel completes, containing all approved orders to be auto-flowed into Transfer Negotiation.

### FR-14: WebSocket Push for Cross-Plant Updates
When the receiving plant planner accepts or rejects a transfer via the Transfer Negotiation UI:
- The frontend sends the decision to the backend via the existing WebSocket connection
- The backend processes the decision (updates order status in DynamoDB via ERP Data MCP)
- The backend pushes an update event to both planners' WebSocket connections containing: updated order statuses, updated capacity metrics
- Both planners' dashboards (Job Status + Operational Efficiency) update in real-time without manual refresh

### FR-15: Transfer Negotiation View — Sender Tab
The sending plant's planner shall see an "Outgoing Transfers" section in Transfer Negotiation showing:
- All orders submitted for transfer with their current status (Submitted for Review, Accepted, Declined)
- Read-only view — sender cannot modify after auto-submission
- Decline reasons visible when Ohio rejects

---

## Non-Functional Requirements

### NFR-01: Three-Column Layout Performance
The three-column layout with the Live Capacity Impact Panel shall render without layout shift or jank. Gauge animations shall complete within 300ms. The panel shall not block interaction with the center column's decision cards.

### NFR-02: Real-Time Update Latency
Cross-plant dashboard updates via WebSocket push shall arrive within 2 seconds of the receiving plant's accept/reject action.

### NFR-03: Accessibility
- Capacity gauges shall include text alternatives (aria-labels with percentage values)
- Accept/Reject buttons shall have clear focus indicators and keyboard navigation
- The three-column layout shall be responsive: on screens < 1280px, the capacity impact panel collapses to a toggleable overlay
- Color-coded gauges shall use patterns/icons in addition to color for colorblind accessibility

### NFR-04: Security Baseline Compliance
- Transfer accept/reject actions shall validate the planner's plant attribute server-side to prevent cross-plant unauthorized actions
- WebSocket push messages shall only be sent to authenticated connections belonging to the relevant plant's planner
- No new API endpoints introduced — all communication via existing WebSocket connection
- Input sanitization on optional decline reason text field

### NFR-05: Data Consistency
Transfer status transitions shall be atomic — if the DynamoDB update fails, the WebSocket push shall not fire, and the UI shall show an error state with retry option.

---

## Extension Compliance

| Extension | Enabled | Status |
|-----------|---------|--------|
| Security Baseline | Yes | Compliant — NFR-04 addresses plant-level authorization, WebSocket auth, input sanitization |

---

## Files Affected (Estimated)

| File | Change Type | Description |
|------|------------|-------------|
| `orchestrator-agent/src/orchestrator_agent/models/schemas.py` | MODIFY | Add `capacityImpact` and `transferOrders` to UiPayload |
| `orchestrator-agent/src/orchestrator_agent/prompts/system_prompt.py` | MODIFY | Instruct LLM to emit capacityImpact at decision points and transferOrders at funnel completion |
| `orchestrator-agent/src/orchestrator_agent/agent.py` | MODIFY | Ensure update_ui captures new fields |
| `infrastructure/streaming-proxy/index.mjs` | MODIFY | Pass through new UI payload fields |
| `frontend-spa/src/types/index.ts` | MODIFY | Add CapacityImpact, TransferOrder types; extend UiPayload |
| `frontend-spa/src/store/index.ts` | MODIFY | Add transfer lifecycle state, capacity impact tracking, cross-plant update actions |
| `frontend-spa/src/lib/responseParser.ts` | MODIFY | Handle new capacityImpact and transferOrders uiData fields |
| `frontend-spa/src/lib/streaming.ts` | MODIFY | Handle WebSocket push events for cross-plant updates |
| `frontend-spa/src/components/transfers/TransferNegotiationView.tsx` | MODIFY | Add Incoming/Outgoing tabs, Accept/Reject per order, sender read-only view |
| `frontend-spa/src/components/disruption/CapacityImpactPanel.tsx` | CREATE | New right-side panel with gauges + delta preview |
| `frontend-spa/src/components/disruption/DisruptionPage.tsx` | MODIFY | Three-column layout during delay/funnel phases |
| `frontend-spa/src/components/disruption/CapacitySummaryStep.tsx` | CREATE | New final stepper step with receiving plant utilization summary |
| `frontend-spa/src/components/dashboard/JobStatusView.tsx` | MODIFY | Show "Transferred In" badges, handle real-time order status updates |
| `frontend-spa/src/components/dashboard/OperationalEfficiencyView.tsx` | MODIFY | Handle real-time utilization updates from WebSocket push |
| `frontend-spa/src/lib/dashboardData.ts` | MODIFY | Support dynamic refresh from WebSocket push events |
| `erp-data-mcp/src/erp_data_mcp/tools/orders.py` | MODIFY | Add transfer status update tool (accept/reject) |

---

## Traceability

| Requirement | User Request Item | Components Affected |
|-------------|-------------------|---------------------|
| FR-01 | Req 1: Approved orders appear as "Submitted for Review" | Orchestrator, Frontend Store, Transfer Negotiation View |
| FR-02, FR-03, FR-09 | Req 2: Ohio reviews with accept/reject | Transfer Negotiation View, Store |
| FR-04, FR-05, FR-06 | Req 3: Both dashboards update | Job Status View, Operational Efficiency View, WebSocket |
| FR-11 | Req 4: Bidirectional | All frontend components (dynamic labels) |
| FR-07, FR-08, FR-09 | Req 5: Live capacity impact panel | CapacityImpactPanel (new), DisruptionPage layout |
| FR-10 | Req 6: Final state summary | CapacitySummaryStep (new), Disruption stepper |
