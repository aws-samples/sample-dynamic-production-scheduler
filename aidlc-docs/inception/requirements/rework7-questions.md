# Rework 7 — Requirements Clarification Questions

## Transfer Negotiation, Live Capacity Impact & Cross-Plant Dashboard Updates

Please answer each question by filling in the letter choice after the `[Answer]:` tag.
If none of the options match your needs, choose the last option (Other) and describe your preference.

---

## Question 1
After the constraint funnel completes and orders are approved for reroute, how should they flow into the Transfer Negotiation view?

A) Automatically — all funnel-approved orders immediately appear in Transfer Negotiation as "Submitted for Review" with no additional Miami planner action
B) Miami planner reviews the funnel results and explicitly confirms which approved orders to submit as transfer requests (current Rework 4 handshake model)
C) Other (please describe after [Answer]: tag below) A

[Answer]: 

## Question 2
On the receiving plant's tab (e.g., Ohio), how should the "Review these orders to include" section be presented?

A) A dedicated sub-tab or section within the existing Transfer Negotiation view, showing incoming orders with Accept/Reject buttons per order
B) A notification-driven approach — Ohio planner gets a banner notification that links to a review modal/overlay with Accept/Reject actions
C) A new column in the Ohio Job Status dashboard showing "Pending Incoming Transfers" with inline Accept/Reject
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
After Ohio accepts/rejects transfers, which dashboards should update and how?

A) Both plants' Job Status views update (transferred orders move to Ohio's active list, removed from Florida's active list) AND both plants' Operational Efficiency views update (Ohio utilization increases, Florida utilization decreases)
B) Only the Job Status views update — Operational Efficiency stays static until a manual refresh
C) All dashboards update plus a summary notification is sent to both planners
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4
For the "Live Capacity Impact" right-side panel during delay optimization and constraint funnel — what data should it show?

A) A compact capacity gauge panel showing both plants' Rolling Mill %, Finishing Line %, and overall utilization — updating in real-time as each decision is made
B) A before/after comparison table showing capacity deltas for the current decision being evaluated (not cumulative)
C) Both — gauges for cumulative running state plus a delta preview for the current pending decision
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 5
Should the live capacity impact panel replace the existing side panel during disruption, or appear as an additional element?

A) Replace the existing side panel entirely during disruption workflow phases (delay optimization + constraint funnel)
B) Appear as a new right-side column alongside the main disruption content (three-column layout: nav | main content | capacity impact)
C) Appear as a collapsible/expandable panel that overlays the right side of the disruption view
D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6
For the "Final State Summary" showing Ohio capacity utilization after all decisions — where should this appear?

A) As the final step in the disruption workflow stepper (after the existing Summary phase), showing a dedicated capacity utilization dashboard for the receiving plant
B) Integrated into the existing Summary phase — add capacity utilization metrics alongside the current summary text
C) As an automatic update to the Ohio planner's Operational Efficiency dashboard view (navigable from the summary)
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
For bidirectional support (Ohio disruption → Florida receives), should the system dynamically swap roles based on which plant is disrupted?

A) Yes — the disruption initiator's plant is always the "sender" and the other plant is always the "receiver." All UI labels, transfer flows, and capacity panels adapt automatically based on the disrupted plant
B) Yes, but with separate hardcoded flows for each direction (Florida→Ohio and Ohio→Florida)
C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8
Should the `update_ui` tool (from Rework 6) be extended to emit capacity impact data for the live panel, or should the frontend calculate it from existing store data?

A) Extend `update_ui` — the orchestrator/agents emit a new `capacityImpact` field in the UI payload with both plants' current and projected utilization after each decision
B) Frontend-calculated — the frontend derives capacity impact from the existing capacity snapshot in the store plus the pending decision's freed/consumed hours
C) Hybrid — agents emit baseline capacity snapshots via `update_ui`, frontend calculates the per-decision delta locally
D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 9
How should the Transfer Negotiation view handle the accept/reject workflow for the receiving plant?

A) Simple accept/reject per order with an optional reason text field
B) Accept/reject per order with mandatory reason for rejection, plus ability to counter-propose (e.g., "accept but delay 3 days")
C) Batch accept/reject — Ohio planner can select multiple orders and approve/reject them together
D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10
Should the cross-plant dashboard updates happen via WebSocket push (real-time) or REST polling?

A) WebSocket push — when Ohio accepts a transfer, the update is pushed to both planners' dashboards in real-time via the existing WebSocket connection
B) REST polling — dashboards periodically refresh data from the REST proxy (every 5-10 seconds during active transfers)
C) Hybrid — WebSocket notification triggers a targeted REST fetch for the updated data
D) Other (please describe after [Answer]: tag below)

[Answer]: a
