# Functional Design Plan — Unit 8: Frontend (React SPA)

## Unit Context

- **Unit**: Frontend — Conversational UI with structured approval interface
- **Type**: Presentation Layer (TypeScript / React / Vite)
- **Primary Story**: US-10 (Streaming Agent Responses)
- **Supporting Stories**: US-01, US-02, US-04, US-05, US-06, US-07, US-08
- **Components**: Chat Interface, Side Panel, WebSocket Client
- **Deployment**: Static SPA on S3 + CloudFront
- **Backend Integration**: WebSocket to Orchestrator Agent via API Gateway

## Generation Steps

- [x] Step 1: Define frontend domain entities (TypeScript interfaces for all message types, session state, capacity tracker, audit entries)
- [x] Step 2: Define WebSocket message protocol (client-to-server and server-to-client message schemas)
- [x] Step 3: Define Chat Interface business logic (message rendering rules, streaming token assembly, agent badge logic, structured data rendering)
- [x] Step 4: Define Side Panel business logic (approval flow state machine, capacity tracker update rules, audit trail display rules, phase progress logic)
- [x] Step 5: Define UI state management model (global state shape, state transitions, WebSocket connection state)
- [x] Step 6: Define frontend business rules (input validation, reconnection policy, error display, accessibility requirements)

## Clarifying Questions

## Question 1
What UI component library should the frontend use?

A) Material UI (MUI) — comprehensive, well-documented, large ecosystem
B) Ant Design — enterprise-focused, rich data display components (tables, forms)
C) Shadcn/ui + Tailwind CSS — lightweight, copy-paste components, full control
D) Chakra UI — accessible by default, simple API
X) Other (please describe after [Answer]: tag below)

[Answer]: something that is accessible as a wrapper on top of erp systems

## Question 2
What state management approach should be used?

A) React Context + useReducer — built-in, no extra dependencies, sufficient for single-user demo
B) Zustand — lightweight, minimal boilerplate, good for medium complexity
C) Redux Toolkit — full-featured, time-travel debugging, overkill for demo but familiar
D) Jotai — atomic state, minimal re-renders, good for streaming updates
X) Other (please describe after [Answer]: tag below)

[Answer]: i have no idea 

## Question 3
How should the chat interface handle long structured data (e.g., 20-order priority tables)?

A) Inline scrollable table within the chat bubble — keeps context in conversation flow
B) Collapsible/expandable section — shows summary, click to expand full table
C) Side panel auto-populates with structured data — chat shows summary text only
D) Combination: summary in chat + "View details" button that opens side panel tab
X) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question 4
How should the approval flow work when the Constraint Matching Agent presents orders one at a time?

A) Side panel shows current order with Approve/Skip/Reject buttons; chat shows agent reasoning
B) Chat-only: inline buttons within the chat message for each order
C) Modal dialog: each order pops up a focused approval dialog with all 4 constraint layers
D) Split view: chat on left with reasoning, dedicated approval card on right with action buttons
X) Other (please describe after [Answer]: tag below)

[Answer]: Combo of A and D

## Question 5
What should happen when the WebSocket connection drops mid-conversation?

A) Auto-reconnect silently with exponential backoff; show subtle "Reconnecting..." indicator
B) Show prominent banner "Connection lost" with manual "Reconnect" button
C) Auto-reconnect + replay missed messages from server-side buffer
D) Auto-reconnect with banner; disable input until reconnected; no message replay (MVP simplicity)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
How should the running capacity tracker in the side panel be visualized?

A) Simple table with Rolling Mill hours, Finishing Line hours, material tons — updated after each decision
B) Progress bars (horizontal) showing used vs available capacity per dimension with color thresholds
C) Combination: progress bars for quick visual + expandable table for exact numbers
D) Gauge/donut charts per dimension with numeric labels
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 7
Should the frontend include a dark mode option for the MVP?

A) Yes — implement dark/light toggle from the start (common expectation for dev tools)
B) No — light mode only for MVP, add dark mode post-MVP
C) System preference only — follow OS dark/light setting automatically, no manual toggle
X) Other (please describe after [Answer]: tag below)

[Answer]: C
