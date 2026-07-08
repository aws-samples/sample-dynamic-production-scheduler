# Frontend Functional Design — Clarification Questions

I detected ambiguities in 3 of your responses that need clarification before I can proceed.

## Ambiguity 1: UI Component Library (Q1)
You said: "something that is accessible as a wrapper on top of erp systems"

This is unclear — none of the original options are ERP wrappers. For a React SPA that communicates with backend agents via WebSocket, the component library is purely a UI toolkit for rendering chat, tables, buttons, etc. It doesn't wrap ERP systems directly (the ERP Data MCP handles that on the backend).

### Clarification Question 1
Given that the frontend is a standalone React SPA (not embedded in an ERP), which UI toolkit should we use for building the chat interface, tables, and approval buttons?

A) Shadcn/ui + Tailwind CSS — lightweight, accessible, full styling control, modern React patterns
B) Material UI (MUI) — comprehensive component library with built-in accessibility and familiar look
C) Ant Design — rich table/form components, enterprise-focused, good for data-heavy UIs
D) No preference — pick the best fit for a chat + data table + approval button interface
X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Ambiguity 2: State Management (Q2)
You said: "i have no idea"

I need a decision here since it affects the entire frontend architecture. Let me simplify:

### Clarification Question 2
For a single-user demo app with WebSocket streaming and approval state, which approach?

A) Zustand — recommended: lightweight, minimal boilerplate, handles streaming updates well, easy to learn
B) React Context + useReducer — zero extra dependencies, built into React, slightly more verbose
C) No preference — use whatever is simplest for this use case
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Ambiguity 3: Approval Flow (Q4)
You said: "Combo of A and D"

Option A = "Side panel shows current order with Approve/Skip/Reject buttons; chat shows agent reasoning"
Option D = "Split view: chat on left with reasoning, dedicated approval card on right with action buttons"

These are very similar — both have chat on left and approval controls on right. The key difference is whether the right side is a persistent side panel (A) or a dedicated approval card (D).

### Clarification Question 3
To clarify the approval flow layout:

A) Persistent side panel (always visible) with tabs: Approval tab shows current order + buttons, Tracker tab shows capacity, Audit tab shows trail. Chat is on the left.
B) Contextual approval card that appears on the right ONLY when an order needs a decision, replacing the side panel content temporarily. Side panel returns to tracker/audit view after decision.
C) No preference — use whichever is simpler to implement while keeping chat + approval visible simultaneously
X) Other (please describe after [Answer]: tag below)

[Answer]: B
