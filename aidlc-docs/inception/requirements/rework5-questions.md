# Rework 5 — UI-Driven Disruption Workflow: Clarification Questions

The current disruption flow is chat-based: the Planner types a message describing a disruption, the orchestrator agent runs the multi-phase workflow, and responses stream back as text with inline approval buttons. You want to shift to a UI-driven flow where clicking a button triggers the orchestrator and the UI adapts based on agent responses.

Please answer each question by filling in the letter choice after the `[Answer]:` tag.

---

## Question 1
How should the disruption workflow be initiated from the UI?

A) A prominent "Start Disruption Response" button on the Dashboard page (replaces the need to go to chat)
B) A new top-level nav item "Disruption" that opens a dedicated disruption wizard page
C) A button on the Dashboard that opens a modal/dialog to collect initial disruption details before starting
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 2
For the initial disruption input (event type, affected plant, description), how should the user provide this?

A) A structured form with dropdowns (event type: tornado/earthquake/fire/etc., plant: Florida/Ohio) and a text field for description
B) A minimal form — just select the affected plant, and the system auto-detects the rest from ERP data
C) Keep the free-text chat input for the initial disruption description, but everything after that becomes UI-driven
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 3
During Round 1 (Impact Assessment + Capacity Analysis running in parallel), how should the UI present progress and results?

A) A stepper/progress bar showing the workflow phases, with live status indicators for each agent, and results rendered as cards/tables when complete
B) A split-view: left side shows agent progress, right side shows results as they come in (impact table + capacity gauges)
C) A single page that progressively reveals sections as each agent completes (impact section appears first, then capacity section)
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 4
During Round 2 — Delay Optimization (approve/reject delay candidates), how should the UI present each candidate?

A) A card-based queue: one card per delay candidate with order details, impact summary, and Approve/Reject buttons — next card appears after decision
B) A table listing all delay candidates at once, with inline Approve/Reject toggles per row, and a "Confirm All" button at the bottom
C) A modal/dialog for each candidate that the user must act on before seeing the next one
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
During Round 2 — Constraint Funnel (order-by-order rerouting decisions), how should the UI present each order?

A) Same card-based queue as delay optimization — one order at a time with constraint funnel results, recommendation, and Approve/Reject/Skip buttons
B) A table showing all orders with their constraint funnel results, allowing batch decisions
C) A Kanban-style board where orders move through columns (Pending → Approved → Rejected → Skipped)
D) Other (please describe after [Answer]: tag below)

[Answer]: A, C

---

## Question 6
Should the chat panel still be available during the UI-driven disruption flow?

A) Yes — keep the chat panel alongside the disruption UI so the Planner can ask what-if questions or get clarifications from the orchestrator at any time
B) No — hide the chat during the disruption flow; all interaction happens through the UI elements
C) Minimized — collapse the chat to a small floating button that can be expanded if needed
D) Other (please describe after [Answer]: tag below)

[Answer]: A (but just for what if)

---

## Question 7
How should the workflow phase transitions work in the UI?

A) Automatic — after the user completes all decisions in a phase, the system automatically moves to the next phase with a brief transition animation
B) Manual — after each phase completes, show a "Proceed to Next Phase" button so the Planner explicitly controls the pace
C) Hybrid — auto-advance for information phases (Round 1 results), manual advance for decision phases (delays, funnel)
D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 8
For the final summary, how should it be presented?

A) A dedicated summary page with executive summary, decision log, capacity utilization charts, and an "Export PDF" option
B) A summary card/section that appears at the end of the disruption flow within the same page
C) Navigate back to the Dashboard with updated order statuses and a notification banner summarizing the disruption response
D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 9
Should the existing side panel (capacity tracker, agent status, order history, audit trail) remain during the disruption flow?

A) Yes — keep the side panel as-is, it provides useful context alongside the new UI-driven flow
B) Redesign — integrate the side panel information directly into the disruption workflow UI (no separate side panel)
C) Contextual — show the side panel but auto-switch its content based on the current disruption phase
D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 10
What happens to the backend orchestrator agent? Should it change?

A) No backend changes — the orchestrator agent stays the same, the frontend just presents its responses differently (parses structured data from the text stream)
B) Modify the orchestrator to return structured JSON responses instead of natural language, so the UI can render them directly
C) Hybrid — orchestrator returns structured JSON for UI-renderable data (tables, decisions) but keeps natural language for explanations and summaries
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---
