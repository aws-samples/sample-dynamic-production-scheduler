# Rework Cycle 4 — Requirements Clarification Questions

Please answer the following questions to help clarify the two-persona dashboard, handshake workflow, notification system, and capacity tuning requirements.

## Question 1
How should the two planners (Ohio and Miami) be identified in the system?

A) Cognito user attributes — each user has a `plant` attribute assigned by admin, and the dashboard auto-filters to their facility
B) Role selection at login — after signing in, the user picks "Ohio Planner" or "Miami Planner" from a dropdown (no Cognito changes)
C) Separate URLs/routes — `/ohio` and `/miami` each show the respective planner's view
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
You mentioned "Miami" planner instead of "Florida" — the current seed data uses "Florida" as the plant name. Should we:

A) Rename the plant from "Florida" to "Miami" everywhere (seed data, agents, frontend)
B) Keep "Florida" as the internal plant name but display "Miami" in the UI
C) Add "Miami" as a new plant alongside Florida (3 plants total)
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3
For the initial dashboard (before any disruption), what data should the "Job Status Tracking" view show?

A) All active production orders for that planner's facility with columns: Order ID, Product Family, Quantity, Due Date, Customer, Status, Machine Type, Rolling Mill Hours, Finishing Line Hours, Raw Material Tons
B) Same as A but also include completed/cancelled orders from the last 30 days
C) A simplified view: Order ID, Product Family, Due Date, Customer Tier, Status only
D) Other (please describe after [Answer]: tag below)

[Answer]: All 3

## Question 4
For the "Operational Efficiency Monitoring" view, what capacity utilization data should be shown for each facility?

A) Machine utilization gauges (Normal/Overtime/Weekend shifts), manpower allocation bar, material inventory levels, and equipment status (online/maintenance/offline)
B) Same as A plus historical trend charts (last 7 days)
C) Simple summary cards: overall utilization %, manpower %, material stock level per type
D) Other (please describe after [Answer]: tag below)

[Answer]: All 3

## Question 5
For the notification system, how should disruption alerts be delivered to planners?

A) In-app toast notifications + a notification bell icon with unread count in the header bar
B) In-app banner alert at the top of the dashboard that persists until acknowledged
C) Both toast notifications and a persistent notification panel/drawer
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6
For the handshake approval process, what should the workflow look like?

A) Miami planner selects orders to transfer from a list → Ohio planner sees pending transfer requests in their dashboard → Ohio planner approves/declines each one individually
B) The AI orchestrator proposes transfer candidates → Miami planner reviews and confirms which to send → Ohio planner approves/declines
C) Same as B but with a batch approval option (Ohio planner can approve/decline all at once or individually)
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 7
When Ohio planner declines a transfer request, what should happen?

A) The order stays at Miami/Florida plant with a "transfer declined" status — Miami planner must find an alternative
B) The order goes back to the AI for re-evaluation with different constraints
C) Miami planner is notified and can modify the request (e.g., adjust timeline, reduce quantity) and resubmit
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 8
For the capacity constraint agent tuning — the current Ohio plant data shows 75% normal utilization for Rolling Mill and 65% for Finishing Line. What realistic utilization rates should we target?

A) Higher baseline: 85-90% normal utilization (tight capacity, minimal surplus — makes transfer decisions more meaningful)
B) Moderate: 80-85% normal utilization (some surplus but not excessive)
C) Keep current rates but add Ohio's own active orders consuming capacity (currently Ohio orders exist in seed data but aren't factored into "committed" hours)
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 9
Should both planners share the same chat/AI conversation, or have independent sessions?

A) Independent sessions — each planner has their own chat with the orchestrator, seeing only their facility's context
B) Shared session — both planners see the same conversation thread and can both interact
C) Independent sessions but with a shared "transfer negotiation" channel for the handshake workflow
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 10
Should the dashboard be the default landing page (replacing the current chat-first interface), or should it be a separate view alongside the chat?

A) Dashboard is the default landing page — chat is accessible via a tab or side panel
B) Split layout — dashboard on one side, chat on the other (like current layout but dashboard replaces the capacity tracker)
C) Keep current chat-first layout but add a "Dashboard" tab/route that shows the facility overview
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11
Should the Security Baseline extension remain enabled for this rework cycle?

A) Yes — continue enforcing security baseline rules
B) No — disable for this cycle
C) Other (please describe after [Answer]: tag below)

[Answer]: A
