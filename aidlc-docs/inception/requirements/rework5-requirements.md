# Requirements Document — Rework 5: UI-Driven Disruption Workflow

## Intent Analysis Summary

- **User Request**: Convert the chat-based disruption response flow to a UI-driven wizard with dedicated navigation, structured forms, card-based decision queues, and Kanban tracking — while keeping the multi-agent backend unchanged
- **Request Type**: Enhancement (major UI rework)
- **Scope Estimate**: Frontend-heavy — new top-level view, multiple new components, store changes, response parser updates
- **Complexity Estimate**: Complex — new navigation flow, multi-phase wizard UI, real-time agent status, Kanban board, chat integration for what-if

---

## Functional Requirements

### FR-01: Disruption Nav Item
A new top-level navigation item "Disruption" shall be added to the AppHeader nav bar alongside Dashboard, AI Assistant, and Transfer Negotiation. Clicking it opens a dedicated disruption workflow page.

### FR-02: Disruption Landing / Initiation
The disruption page shall display a landing state when no disruption is active. It shows a "Start Disruption Response" action with a minimal form: a plant selector dropdown (Florida / Ohio). On submit, the system sends an auto-generated disruption prompt to the orchestrator agent (e.g., "A disruption has been reported at the [plant] plant. Begin disruption response workflow.") and transitions to the active workflow view.

### FR-03: Workflow Phase Stepper
The disruption page shall display a horizontal stepper/progress bar at the top showing all workflow phases: Disruption Detected → Round 1 (Intelligence) → Delay Optimization → Constraint Funnel → Summary. The current phase is highlighted. Completed phases show a checkmark.

### FR-04: Round 1 — Split-View Results
During Round 1 (Impact Assessment + Capacity Analysis running in parallel), the UI shall display a split-view layout:
- Left side: Agent progress indicators (running/complete status for Impact Assessment and Capacity & Optimization agents)
- Right side: Results rendered as they arrive — impact assessment table (prioritized orders with P1/P2/P3 tags) and capacity gauges (5 dimensions)
- Auto-advance to next phase when both agents complete (hybrid transition per FR-09)

### FR-05: Round 2 — Delay Optimization Card Queue
During the delay optimization phase, the UI shall present delay candidates one at a time as cards. Each card shows:
- Order ID, product family, customer name, customer tier
- Current due date and delay impact summary
- Freed capacity if delayed
- Approve / Reject buttons
After the user decides on a card, the next candidate card appears. A running tally of freed capacity is shown.

### FR-06: Round 2 — Constraint Funnel with Kanban
During the constraint funnel phase, the UI shall present orders using a combined approach:
- Primary: Card-based queue showing one order at a time with constraint funnel results (4-layer pass/fail), recommendation, and Approve / Reject / Skip buttons
- Secondary: A Kanban-style board visible alongside the card, showing all orders in columns: Pending → Approved → Rejected → Skipped. As the user makes decisions, orders move between columns in real-time.
- A "Skip Remaining" button to end the funnel early.

### FR-07: Chat Panel for What-If
The chat panel shall remain accessible during the disruption flow, but scoped to what-if questions. It appears as a collapsible panel (not the full chat view) that the Planner can expand to ask the orchestrator what-if questions (e.g., "What if I add weekend shifts?"). Responses stream back in the chat panel. The disruption UI updates if the what-if changes capacity or order data.

### FR-08: Summary — Dashboard Return
When the disruption workflow completes, the system shall navigate back to the Dashboard view with:
- Updated order statuses reflecting all decisions made during the disruption flow
- A notification banner summarizing the disruption response (orders transferred, capacity utilization, key decisions)

### FR-09: Hybrid Phase Transitions
Phase transitions shall follow a hybrid model:
- Auto-advance for information phases (Round 1 results complete → auto-move to delay optimization)
- Manual advance for decision phases (delay optimization complete → show "Proceed to Constraint Funnel" button; constraint funnel complete → show "Generate Summary" button)

### FR-10: Side Panel Integration
The existing side panel shall NOT be shown during the disruption flow. Instead, all relevant information (capacity tracker, agent status, order history) shall be integrated directly into the disruption workflow UI layout.

### FR-11: No Backend Changes
The orchestrator agent and sub-agents remain unchanged. The frontend continues to parse natural language responses from the orchestrator's text stream using the existing responseParser.ts pattern. New parsing patterns may be added to extract structured data for the UI components.

### FR-12: Active Disruption State
The store shall track an active disruption session with: current phase, disruption plant, agent statuses, delay decisions, funnel decisions, capacity snapshots, and Kanban board state. This state drives the disruption page rendering.

### FR-13: Disruption Page Routing Guard
If a disruption is already in progress and the user navigates away and back to the Disruption nav item, the page shall resume showing the current phase (not restart).

---

## Non-Functional Requirements

### NFR-01: Responsive Layout
The disruption workflow UI shall be responsive and usable on screens 1024px and wider. The split-view in Round 1 shall stack vertically on narrower screens.

### NFR-02: Transition Animations
Phase transitions shall include brief (200-300ms) fade/slide animations to provide visual continuity.

### NFR-03: Accessibility
All interactive elements (buttons, cards, Kanban columns) shall have appropriate ARIA labels, keyboard navigation support, and focus management.

### NFR-04: Performance
The Kanban board shall handle up to 50 orders without perceptible lag. Card transitions shall be smooth (< 100ms render).

### NFR-05: Security Baseline
All existing security patterns (SigV4 signing, Cognito auth, input sanitization) continue to apply. No new API endpoints are introduced.

---

## Extension Compliance

| Extension | Enabled | Status |
|-----------|---------|--------|
| Security Baseline | Yes | Compliant — no new endpoints, existing auth patterns preserved |
