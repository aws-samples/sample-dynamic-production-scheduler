# Integration Test Instructions — Rework 7

## Test Scenarios

### T1: Auto-Flow from Constraint Funnel to Transfer Negotiation (FR-01)
1. Log in as Miami planner, start a disruption workflow for Florida
2. Complete Round 1, delay optimization, and constraint funnel — approve several orders
3. Click "Finish & View Summary" to advance to Capacity Summary
4. Switch to Ohio planner (plant switcher)
5. Navigate to Transfer Negotiation tab
6. **Verify**: Incoming Transfers tab shows all funnel-approved orders with status "Submitted for Review"
7. **Verify**: Each card shows Order ID, Product, Customer, Tier, Value, Due Date, Priority, AI Reasoning

### T2: Accept/Reject Transfers (FR-02, FR-03)
1. As Ohio planner on Transfer Negotiation → Incoming tab
2. Click "Accept" on one order
3. **Verify**: Order disappears from incoming list, status changes to "Accepted"
4. Click "Reject" on another order, enter a reason
5. **Verify**: Order disappears from incoming list, status changes to "Declined" with reason
6. Switch to Miami planner → Transfer Negotiation → Outgoing tab
7. **Verify**: Accepted order shows "Accepted" badge, rejected order shows "Declined" with reason

### T3: Cross-Plant Dashboard Updates (FR-04, FR-05)
1. After accepting transfers as Ohio planner
2. Navigate to Dashboard → Job Status
3. **Verify**: Accepted orders appear with "↓ From Miami" indigo badge
4. **Verify**: "Transferred In" summary card shows correct count
5. **Verify**: Filter dropdown includes "Transferred In" option and filters correctly
6. Switch to Miami planner → Dashboard → Job Status
7. **Verify**: Transferred orders show "Transferred to Ohio" status

### T4: Live Capacity Impact Panel (FR-07, FR-08)
1. Start a disruption workflow as Miami planner
2. Complete Round 1, advance to delay optimization
3. **Verify**: Three-column layout appears — main content left, CapacityImpactPanel right
4. **Verify**: Panel shows "Live Capacity Impact" with receiver (Ohio) and sender (Miami) gauges
5. **Verify**: Gauges are color-coded (green/yellow/red based on utilization %)
6. Make a delay decision (approve)
7. **Verify**: Gauges update to reflect new cumulative state
8. **Verify**: Delta preview shows "+X% if approved" before each decision
9. Advance to constraint funnel
10. **Verify**: Panel persists with updated baseline

### T5: Capacity Summary Step (FR-10)
1. Complete the constraint funnel, click "Finish & View Summary"
2. **Verify**: PhaseStepper shows "Capacity Summary" as the active step (5th step)
3. **Verify**: CapacitySummaryStep shows Ohio plant final utilization gauges
4. **Verify**: Stats show orders absorbed, deferred, skipped counts
5. Click "Return to Dashboard"
6. **Verify**: Navigates to dashboard, disruption session cleared, notification added

### T6: Bidirectional Support (FR-11)
1. Log in as Ohio planner, start a disruption for Ohio
2. **Verify**: Capacity Impact Panel labels show "Ohio (Disrupted)" and "Miami (Receiving)"
3. Complete the workflow
4. Switch to Miami planner → Transfer Negotiation
5. **Verify**: Incoming tab shows orders from Ohio for Miami to review
6. **Verify**: All labels are dynamically swapped (not hardcoded to Florida→Ohio)

### T7: Notification on Transfer Decisions (FR-06)
1. As Ohio planner, accept a transfer
2. **Verify**: Notification bell shows new notification for Miami planner
3. Switch to Miami planner
4. **Verify**: Notification says "Order [ID] transfer accepted"
5. Reject a transfer with reason
6. **Verify**: Miami planner gets "Order [ID] transfer declined: [reason]" notification

### T8: PhaseStepper Progression
1. Start disruption, verify stepper shows 5 steps: Intelligence Gathering → Delay Optimization → Constraint Funnel → Capacity Summary → Complete
2. Progress through each phase
3. **Verify**: Completed steps show green checkmarks, current step is blue, future steps are gray
4. **Verify**: Connector lines turn green as phases complete

## Security Tests

### S1: Input Sanitization on Reject Reason
1. In Transfer Negotiation, reject an order with reason containing `<script>alert('xss')</script>`
2. **Verify**: Script tags are not executed, reason is displayed as plain text

### S2: Lambda Proxy Field Allowlist
1. Send a crafted response with unknown fields in the `ui` object (e.g., `ui.malicious`)
2. **Verify**: Unknown fields are stripped by the Lambda proxy's ALLOWED_UI_KEYS filter
3. **Verify**: `capacityImpact` and `transferOrders` pass through correctly

## Performance Tests

### P1: Three-Column Layout Rendering
1. During delay optimization with capacity impact panel visible
2. **Verify**: No layout shift or jank when making decisions
3. **Verify**: Gauge animations complete within 300ms

### P2: Transfer Negotiation with Many Orders
1. Simulate 20+ transfer orders in the store
2. **Verify**: Incoming/Outgoing tabs render without perceptible lag
3. **Verify**: Accept/Reject actions respond within 200ms
