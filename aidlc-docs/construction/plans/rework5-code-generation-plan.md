# Code Generation Plan — Rework 5: UI-Driven Disruption Workflow

## Unit Context
- **Unit**: frontend-spa (single unit, brownfield)
- **Scope**: New disruption page, new components, store extensions, type additions, nav update, App routing
- **Backend**: No changes — orchestrator returns same text stream, frontend parses it differently
- **Requirements**: FR-01 through FR-13, NFR-01 through NFR-05

## Code Generation Steps

### Stream A: Types & Store Foundation

- [x] **Step 1**: Extend `frontend-spa/src/types/index.ts` — Add disruption workflow types:
  - `DisruptionPhase` type (landing, round1, delay_optimization, constraint_funnel, summary, complete)
  - `DisruptionSession` interface (phase, plant, sessionId, agentStatuses, impactResults, capacityResults, delayDecisions, funnelDecisions, kanbanColumns)
  - `DelayCandidate` interface (orderId, order, freedCapacity, impactSummary)
  - `FunnelOrder` interface (orderId, order, funnelResults, recommendation, reasoning)
  - `KanbanColumn` type and `KanbanState` interface
  - Update `AppView` to include `"disruption"`

- [x] **Step 2**: Extend `frontend-spa/src/store/index.ts` — Add disruption slice:
  - `disruption: DisruptionSession | null` state
  - Actions: `startDisruption(plant)`, `setDisruptionPhase(phase)`, `setImpactResults(data)`, `setCapacityResults(data)`, `addDelayDecision(orderId, decision)`, `addFunnelDecision(orderId, decision)`, `moveFunnelOrder(orderId, column)`, `clearDisruption()`
  - `setDisruptionAgentStatus(agentName, status)` action

### Stream B: Disruption Page Components

- [x] **Step 3**: Create `frontend-spa/src/components/disruption/DisruptionPage.tsx` — Main page component:
  - Renders PhaseSteppper at top
  - Conditionally renders phase views based on `disruption.phase`
  - Landing state when no active disruption
  - Collapsible what-if chat panel at bottom

- [x] **Step 4**: Create `frontend-spa/src/components/disruption/DisruptionLanding.tsx` — Landing/initiation view:
  - Plant selector dropdown (Florida / Ohio)
  - "Start Disruption Response" button
  - On submit: calls `startDisruption(plant)`, sends auto-generated prompt to orchestrator via `sendMessage()`

- [x] **Step 5**: Create `frontend-spa/src/components/disruption/PhaseStepper.tsx` — Horizontal phase stepper:
  - Shows all phases: Disruption Detected → Intelligence Gathering → Delay Optimization → Constraint Funnel → Complete
  - Current phase highlighted, completed phases show checkmark
  - Responsive (horizontal on desktop, compact on tablet)

- [x] **Step 6**: Create `frontend-spa/src/components/disruption/Round1SplitView.tsx` — Split-view for Round 1:
  - Left panel: Agent status cards (Impact Assessment, Capacity & Optimization) with running/complete indicators
  - Right panel: Impact results table (orders with P1/P2/P3 tags) + capacity gauges (5 dimensions)
  - Progressive reveal as agents complete
  - Auto-advance to delay phase when both complete

- [x] **Step 7**: Create `frontend-spa/src/components/disruption/DelayCardQueue.tsx` — Card-based delay candidate queue:
  - Shows one delay candidate card at a time
  - Card displays: order details, impact summary, freed capacity
  - Approve / Reject buttons with transition animation to next card
  - Running tally of total freed capacity
  - "Proceed to Constraint Funnel" button when all candidates processed

- [x] **Step 8**: Create `frontend-spa/src/components/disruption/KanbanBoard.tsx` — Kanban board component:
  - 4 columns: Pending, Approved, Rejected, Skipped
  - Order cards show orderId, product, customer, priority badge
  - Cards move between columns as decisions are made
  - Column counts displayed in headers

- [x] **Step 9**: Create `frontend-spa/src/components/disruption/ConstraintFunnelView.tsx` — Combined card queue + Kanban:
  - Left side: Current order card with funnel results (4-layer pass/fail), recommendation, Approve/Reject/Skip buttons
  - Right side: KanbanBoard showing all orders
  - "Skip Remaining" button
  - "Generate Summary" button when all orders processed

- [x] **Step 10**: Create `frontend-spa/src/components/disruption/WhatIfChat.tsx` — Collapsible what-if chat panel:
  - Collapsed by default (floating button "Ask What-If")
  - Expands to a compact chat input + message list
  - Sends messages via existing `sendMessage()` from streaming.ts
  - Responses parsed and displayed in the chat panel

### Stream C: Navigation, Routing & Parser Integration

- [x] **Step 11**: Modify `frontend-spa/src/components/AppHeader.tsx` — Add "Disruption" nav item:
  - Add `{ view: "disruption", label: "Disruption", icon: AlertTriangle, testId: "nav-disruption" }` to NAV_ITEMS
  - Import AlertTriangle from lucide-react

- [x] **Step 12**: Modify `frontend-spa/src/App.tsx` — Add disruption view routing:
  - Import DisruptionPage
  - Add `{currentView === "disruption" && <DisruptionPage />}` rendering

- [x] **Step 13**: Modify `frontend-spa/src/lib/responseParser.ts` — Add disruption-specific parsing:
  - New function `parseDisruptionResponse(text)` that extracts:
    - Impact assessment results (order tables with priority tags)
    - Capacity analysis results (dimension values)
    - Delay candidates (order details + freed capacity)
    - Funnel results (4-layer pass/fail per order)
    - Phase transitions
  - Calls disruption store actions to update state
  - Existing `parseResponse()` delegates to `parseDisruptionResponse()` when disruption is active

- [x] **Step 14**: Modify `frontend-spa/src/lib/streaming.ts` — No changes needed — Wire disruption flow:
  - In `handleCompleteResponse()`, check if disruption is active and route to disruption parser
  - `sendDisruptionMessage(message)` helper that sends via existing `sendMessage()` but tags as disruption context

- [x] **Step 15**: Summary completion — Handled in DisruptionPage handleFinish() — Update dashboard on disruption complete:
  - When disruption phase reaches "complete", navigate to dashboard view
  - Add notification banner with disruption summary
  - Update order statuses in facilityData based on decisions made

### Documentation

- [x] **Step 16**: Create `aidlc-docs/construction/frontend/code/rework5-code-generation-summary.md` — Summary of all changes
