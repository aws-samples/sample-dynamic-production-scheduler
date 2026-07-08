# Business Rules — Unit 8: Frontend

## BR-FE-01: Message Input Validation
- Message text must be non-empty and trimmed before sending
- Maximum message length: 2000 characters
- Input field disabled when `connection.status !== "connected"`
- Input field disabled when `isAgentTyping === true` (wait for agent to finish)
- Send on Enter key; Shift+Enter for newline

## BR-FE-02: Streaming Token Assembly
- Tokens appended to ChatMessage.content in arrival order
- If a token arrives for an unknown messageId, create a new ChatMessage with role="assistant"
- While streaming (`done=false`): show typing indicator cursor at end of message
- On `done=true`: remove cursor, mark `isStreaming=false`
- If no token received for 30 seconds during active stream, show "Agent is taking longer than expected..." hint (not an error)

## BR-FE-03: Agent Badge Display
- Badge shown above the first message from each agent in a contiguous sequence
- Badge text = agent name (e.g., "Impact Assessment Agent")
- Badge persists on historical messages (not just active)
- Color mapping (consistent):
  - Orchestrator Agent: blue
  - Impact Assessment Agent: orange
  - Capacity & Optimization Agent: green
  - Constraint Matching Agent: purple

## BR-FE-04: Structured Data "View Details" Flow
- Chat bubble shows summary text (e.g., "8 P1, 7 P2, 5 P3 orders classified")
- "View details" button appended below summary
- On click: side panel switches to detail mode, renders full data table
- Close button in detail view returns side panel to previous mode
- Multiple "View details" buttons in chat history all remain clickable

## BR-FE-05: Approval Card Rules
- Approval card appears ONLY when `order_decision_request` ServerMessage arrives
- Card replaces side panel content (capacity tracker hidden temporarily)
- All three buttons (Approve/Skip/Reject) enabled simultaneously
- On any button click: send decision, disable all buttons, show "Sending..." state
- After backend acknowledges (next message or next decision request): return to tracker view
- If user has not decided and a new `order_decision_request` arrives: replace current card with new order

## BR-FE-06: Capacity Tracker Update Rules
- Tracker updated ONLY when `capacity_update` ServerMessage arrives (not computed client-side)
- Progress bar color thresholds:
  - Green: utilization < 70%
  - Yellow: utilization 70-89%
  - Red: utilization >= 90%
- Bottleneck label updated with each capacity update
- "Show details" toggle expands to numeric table (used, available, percentage per dimension)
- Tracker persists across panel mode switches (state preserved in Zustand store)

## BR-FE-07: Phase Progress Display
- Phase progress bar always visible at top of side panel
- Phases displayed left-to-right: Intake > Impact > Capacity > Delays > Funnel > What-If > Summary
- Current phase: highlighted/active indicator
- Completed phases: checkmark indicator
- Future phases: dimmed/inactive
- Updated when `phase_update` ServerMessage arrives

## BR-FE-08: WebSocket Reconnection Policy
- Auto-reconnect with exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (cap)
- Subtle "Reconnecting..." indicator in app header (not modal, not blocking)
- Input field disabled during reconnection
- On reconnect success: hide indicator, re-enable input
- No message replay — user sees gap in conversation if messages were missed
- Session ID preserved across reconnections

## BR-FE-09: Error Display Rules
- WebSocket errors: subtle header indicator (not modal)
- Backend error messages (type="error"): render as ChatMessage with role="assistant", red-tinted bubble, agent="System"
- Never display raw error objects, stack traces, or internal details to user
- Generic fallback: "Something went wrong. Please try again."

## BR-FE-10: Audit Trail Display
- Collapsible section at bottom of side panel
- Shows most recent 20 entries (scrollable within fixed height)
- Each entry: timestamp (relative, e.g., "2m ago"), agent badge, action summary
- Auto-scrolls to newest entry on update
- Click entry to expand full details text

## BR-FE-11: Dark Mode (System Preference)
- Detect via CSS `prefers-color-scheme: dark` media query
- Tailwind `dark:` class variants applied automatically
- No manual toggle in MVP
- All components must define both light and dark color tokens
- Shadcn/ui CSS variables handle theme switching

## BR-FE-12: Accessibility Requirements
- All interactive elements must be keyboard navigable (Tab order)
- Approval buttons must have `aria-label` attributes (e.g., "Approve order PO-2026-001")
- Chat messages must use `role="log"` and `aria-live="polite"` for screen reader announcements
- Progress bars must have `aria-valuenow`, `aria-valuemin`, `aria-valuemax` attributes
- Color is never the sole indicator — always paired with text or icon
- Focus management: when approval card appears, focus moves to first action button
- Minimum touch target: 44x44px for all buttons

## BR-FE-13: Data-TestId Convention
- All interactive elements include `data-testid` attribute
- Naming: `{component}-{element}-{role}`
- Examples:
  - `chat-input-field`, `chat-send-btn`
  - `approval-card-approve-btn`, `approval-card-skip-btn`, `approval-card-reject-btn`
  - `tracker-rolling-mill-bar`, `tracker-details-toggle`
  - `phase-progress-bar`, `audit-trail-toggle`
  - `side-panel-close-btn`, `detail-view-close-btn`
