# Code Generation Plan — Rework 7: Transfer Negotiation, Live Capacity Impact & Cross-Plant Dashboard Updates

## Context
- **Project Type**: Brownfield
- **Requirements**: rework7-requirements.md (15 FR + 5 NFR)
- **Execution Plan**: rework7-execution-plan.md (4 streams, ~17 steps)

## Stream A: Backend — Orchestrator Schema & Prompt Updates

### Step 1: Extend UiPayload Pydantic Schema (FR-12, FR-13)
- [x] MODIFY `orchestrator-agent/src/orchestrator_agent/models/schemas.py`
- Add `UiCapacityImpactPlant` model: name, rollingMill (current/projected), finishingLine (current/projected), overall (current/projected)
- Add `UiCapacityImpact` model: senderPlant (UiCapacityImpactPlant), receiverPlant (UiCapacityImpactPlant)
- Add `UiTransferOrder` model: orderId, product, customer, customerTier, value, dueDate, priority, recommendation, reasoning, funnelResults
- Add `capacityImpact: UiCapacityImpact | None = None` to UiPayload
- Add `transferOrders: list[UiTransferOrder] | None = None` to UiPayload

### Step 2: Update Orchestrator System Prompt (FR-12, FR-09)
- [x] MODIFY `orchestrator-agent/src/orchestrator_agent/prompts/system_prompt.py`
- Add instructions for when to emit `capacityImpact` field:
  - At start of delay optimization (baseline snapshot)
  - After each delay decision (updated cumulative state)
  - At start of constraint funnel (post-delay baseline)
  - After each funnel decision (updated cumulative state)
- Add instructions for `transferOrders` field:
  - Emit when constraint funnel completes with all approved orders
- Add schema examples for both new fields

### Step 3: Verify Lambda Proxy Passthrough (FR-12)
- [x] VERIFY `infrastructure/streaming-proxy/index.mjs`
- Confirm the proxy passes through all fields in the `ui` object (it should already since it forwards the entire envelope)
- No changes expected — the proxy already forwards `ui` as-is

---

## Stream B: Frontend — Types, Store & Response Parser

### Step 4: Extend TypeScript Types (FR-09, FR-12, FR-13)
- [ ] MODIFY `frontend-spa/src/types/index.ts`
- Add `UiCapacityImpactPlant` interface: name, rollingMill: {current, projected}, finishingLine: {current, projected}, overall: {current, projected}
- Add `UiCapacityImpact` interface: senderPlant, receiverPlant
- Add `UiTransferOrder` interface: orderId, product, customer, customerTier, value, dueDate, priority, recommendation, reasoning, funnelResults
- Extend `UiPayload` with: capacityImpact?: UiCapacityImpact | null, transferOrders?: UiTransferOrder[] | null
- Add `"capacity_summary"` to `DisruptionPhase` type
- Extend `TransferStatus` with `"submitted_for_review"`
- Extend `ProductionOrder` with optional `transferredFrom?: PlantId | null` field

### Step 5: Extend Zustand Store (FR-01, FR-03, FR-04, FR-05, FR-08, FR-14)
- [ ] MODIFY `frontend-spa/src/store/index.ts`
- Add to `DisruptionSession`: `capacityImpact: UiCapacityImpact | null`
- Add store actions:
  - `setDisruptionCapacityImpact(impact: UiCapacityImpact)` — updates live capacity impact panel data
  - `autoFlowTransferOrders(orders: UiTransferOrder[])` — creates TransferRequest entries with status "submitted_for_review" from funnel-approved orders
  - `acceptTransfer(transferId: string, reason?: string)` — updates transfer status to "approved", adds order to receiving plant's facilityData
  - `rejectTransfer(transferId: string, reason?: string)` — updates transfer status to "declined" with reason
  - `applyTransferToDashboards(transferId: string)` — updates both plants' facilityData (orders + capacity)

### Step 6: Update Response Parser (FR-09, FR-01)
- [ ] MODIFY `frontend-spa/src/lib/responseParser.ts`
- Handle `uiData.capacityImpact` — call `store.setDisruptionCapacityImpact()`
- Handle `uiData.transferOrders` — call `store.autoFlowTransferOrders()` to auto-create transfer requests
- Add `"capacity_summary"` to phase mapping

### Step 7: Update Streaming for WebSocket Push (FR-14)
- [ ] MODIFY `frontend-spa/src/lib/streaming.ts`
- Add handler for incoming WebSocket push events of type `transfer_update`
- When received: update transfer request status in store, trigger dashboard data refresh
- Add handler for `dashboard_sync` push events that update facilityData for both plants

---

## Stream C: Frontend — Disruption UI (Live Capacity Impact + Summary Step)

### Step 8: Create CapacityImpactPanel Component (FR-07, FR-08)
- [x] CREATE `frontend-spa/src/components/disruption/CapacityImpactPanel.tsx`
- Reads `disruption.capacityImpact` from store
- Renders two sections: Sender Plant gauges + Receiver Plant gauges
- Each plant shows: Rolling Mill %, Finishing Line %, Overall %
- Color-coded: green (<70%), yellow (70-85%), red (>85%)
- Delta preview section: shows projected change for current pending decision
- Calculates delta from `capacityImpact.receiverPlant.projected - capacityImpact.receiverPlant.current`
- Labels adapt based on disruption.plant (bidirectional — FR-11)
- Responsive: collapses to overlay on screens < 1280px
- `data-testid="capacity-impact-panel"`

### Step 9: Update DisruptionPage to Three-Column Layout (FR-07)
- [x] MODIFY `frontend-spa/src/components/disruption/DisruptionPage.tsx`
- During `delay_optimization` and `constraint_funnel` phases: render three-column layout
  - Left: PhaseStepper (existing, moved to sidebar)
  - Center: Main content (DelayCardQueue or ConstraintFunnelView)
  - Right: CapacityImpactPanel (new)
- During `round1` and `complete` and `capacity_summary` phases: keep existing single-column layout
- Use CSS grid: `grid-cols-[auto_1fr_320px]` for three-column, `max-w-6xl` for single-column

### Step 10: Create CapacitySummaryStep Component (FR-10)
- [x] CREATE `frontend-spa/src/components/disruption/CapacitySummaryStep.tsx`
- Reads `disruption.capacityImpact` from store for final state
- Shows receiving plant's final utilization across all dimensions
- Before vs. after comparison (uses first capacityImpact snapshot vs. final)
- Visual gauges matching Operational Efficiency view style
- Counts: orders absorbed, orders deferred, total capacity consumed
- "Return to Dashboard" button navigates to receiving plant's dashboard
- `data-testid="capacity-summary-step"`

### Step 11: Update PhaseStepper (FR-10)
- [x] MODIFY `frontend-spa/src/components/disruption/PhaseStepper.tsx`
- Add `{ phase: "capacity_summary", label: "Capacity Summary" }` step between "Constraint Funnel" and "Complete"
- Update `PHASE_ORDER` to include `"capacity_summary"`
- Update phase index logic

### Step 12: Update DisruptionPage Phase Routing (FR-10, FR-11)
- [x] MODIFY `frontend-spa/src/components/disruption/DisruptionPage.tsx`
- Add `capacity_summary` phase rendering → `<CapacitySummaryStep />`
- Update `handleFinish` to navigate through capacity_summary before complete
- Add bidirectional label logic: derive sender/receiver plant names from `disruption.plant`

---

## Stream D: Frontend — Transfer Negotiation & Dashboard Updates

### Step 13: Rework TransferNegotiationView (FR-01, FR-02, FR-03, FR-15)
- [x] MODIFY `frontend-spa/src/components/transfers/TransferNegotiationView.tsx`
- Add tab navigation: "Incoming Transfers" / "Outgoing Transfers" (based on planner's plant)
- **Incoming tab** (receiving plant): Shows orders with status "submitted_for_review" destined for this plant
  - Each order card shows: Order ID, Product, Customer, Tier, Value, Due Date, Priority, AI Reasoning
  - Accept / Reject buttons per order with optional reason text field
  - Header: "Review these orders to include in your production schedule"
  - On Accept: call `store.acceptTransfer()`, send WebSocket message
  - On Reject: call `store.rejectTransfer()`, send WebSocket message
- **Outgoing tab** (sending plant): Read-only list of submitted orders with status badges
  - Shows decline reasons when available
- Bidirectional: tabs adapt based on `planner.plant` vs transfer direction

### Step 14: Update JobStatusView (FR-04)
- [x] MODIFY `frontend-spa/src/components/dashboard/JobStatusView.tsx`
- Add "Transferred In" badge for orders with `transferredFrom` field set
- Add "Transferred to [Plant]" status display
- Add filter option for "Transferred In" status
- Update summary cards: add "Transferred In" count card
- Support real-time updates from WebSocket push (re-render when facilityData changes)

### Step 15: Update Dashboard Data for Cross-Plant Sync (FR-05, FR-14)
- [x] MODIFY `frontend-spa/src/lib/dashboardData.ts`
- Add `applyTransferToFacilityData()` function: given a transfer acceptance, update both plants' facilityData
  - Sender: mark order as "Transferred to [Plant]"
  - Receiver: add order to active list with "Transferred In" badge, update capacity metrics
- Add `refreshFacilityDataFromStore()` function for WebSocket-triggered refreshes

### Step 16: Add Cross-Plant Notification Logic (FR-06)
- [x] MODIFY `frontend-spa/src/store/index.ts`
- In `acceptTransfer` and `rejectTransfer` actions: dispatch notifications to both planners
- Accept notification: "Order [ID] transfer accepted by [Plant]"
- Reject notification: "Order [ID] transfer declined by [Plant]: [reason]"
- Summary notification after all transfers decided: total transferred, total declined, net capacity impact

### Step 17: Add Transfer Decision WebSocket Messages (FR-14)
- [x] MODIFY `frontend-spa/src/lib/streaming.ts`
- Add `sendTransferDecision(transferId, decision, reason?)` function
- Sends via existing HTTP POST endpoint with type "transfer_decision"
- Backend processes and pushes update to both planners' connections

---

## Summary

| Stream | Steps | Files Modified | Files Created |
|--------|-------|---------------|---------------|
| A: Backend | 1-3 | 2 (schemas.py, system_prompt.py) + 1 verify | 0 |
| B: Frontend Types/Store | 4-7 | 4 (types, store, responseParser, streaming) | 0 |
| C: Disruption UI | 8-12 | 2 (DisruptionPage, PhaseStepper) | 2 (CapacityImpactPanel, CapacitySummaryStep) |
| D: Transfer/Dashboard | 13-17 | 4 (TransferNegotiationView, JobStatusView, dashboardData, streaming) | 0 |
| **Total** | **17** | **12 modified** | **2 created** |

## Dependencies
- Stream A and B can execute in parallel (no dependencies)
- Stream C depends on Stream B (types + store must exist first)
- Stream D depends on Stream B (types + store must exist first)
- Steps within each stream are sequential
