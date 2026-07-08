# Rework Cycle 3 — UI Update Questions

You mentioned you need user interface updates as well. The current frontend has:
- Chat panel (left) with message streaming, markdown rendering, agent badges
- Side panel (right) with phase progress bar, capacity tracker, approval card, audit trail
- WebSocket connection with stream_token support

Please answer the following questions about what UI improvements you want.

---

## Question 1: What UI issues did you observe during the live test?
What specific problems or missing features did you notice in the frontend during the live test?

A) The chat messages were hard to read — need better formatting for tables, order lists, and structured data
B) The side panel wasn't updating — capacity tracker and phase progress stayed empty/stale
C) The approval workflow didn't trigger — the approval card never appeared for order decisions
D) The streaming was broken or laggy — messages appeared all at once instead of streaming
E) Multiple issues (please list the specific problems after [Answer]: tag below)
F) Other (please describe after [Answer]: tag below)

[Answer]: A, B, C, D

## Question 2: Phase Progress Bar
The phase progress bar shows 7 phases (Intake, Impact, Capacity, Delays, Funnel, What-If, Summary). During the live test, did it update correctly?

A) It never updated — stayed on "idle" the whole time
B) It updated but the phases don't match the actual workflow steps observed in the live test
C) It worked fine — no changes needed
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3: Capacity Tracker
The capacity tracker shows 4 dimensions (Rolling Mill, Finishing Line, Material Tons, Operator Hours) with progress bars. What changes are needed?

A) It never received data — always showed "Waiting for capacity data..."
B) It received data but the values were wrong or didn't update as decisions were made
C) It works but needs visual improvements (e.g., color coding for warning thresholds, better layout)
D) No changes needed
E) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4: Order Decision Approval Card
The approval card shows order details, funnel results, and approve/skip/reject buttons. What changes are needed?

A) It never appeared — the agent didn't send order_decision_request messages
B) It appeared but was missing information or had wrong data
C) It needs UX improvements (e.g., better layout, more context, keyboard shortcuts)
D) No changes needed
E) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5: Chat Message Rendering
The chat panel renders markdown with tables and code blocks. What improvements are needed?

A) Tables from the agent are not rendering properly — need better table formatting
B) Long agent responses are hard to scan — need collapsible sections or summary views
C) Need visual distinction between different agent responses (orchestrator vs sub-agents)
D) Chat rendering is fine — no changes needed
E) Other (please describe after [Answer]: tag below)

[Answer]: A,B,C

## Question 6: New UI Features
Are there any new UI features you want to add?

A) Real-time sub-agent status indicators (show which sub-agent is currently working)
B) Order decision history panel (show all decisions made so far with running totals)
C) Export/download capability for the final disruption report
D) Dark/light theme toggle
E) Multiple features (please list after [Answer]: tag below)
F) Other (please describe after [Answer]: tag below)

[Answer]: A,B
Also need mapping like interactive view, look at this demo urls for examples
https://d1nthyz9yleova.cloudfront.net/a31295c5-9664-44a0-a832-09e70820f9ac:idea-001/html/cascade-impact-simulator.html
https://d1nthyz9yleova.cloudfront.net/a31295c5-9664-44a0-a832-09e70820f9ac:idea-001/html/procurement-sales-alignment-scorecard.html
https://dltq86rigxzcd.cloudfront.net/dashboard/transfers

## Question 7: Mobile/Responsive Design
Does the UI need to work on mobile or tablet devices?

A) Yes — needs full responsive design for mobile and tablet
B) Partial — tablet landscape is enough, no phone support needed
C) No — desktop only is fine
D) Other (please describe after [Answer]: tag below)

[Answer]: B
