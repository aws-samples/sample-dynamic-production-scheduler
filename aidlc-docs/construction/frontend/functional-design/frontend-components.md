# Frontend Components — Unit 8

## Component Hierarchy

```
App
  +-- AppHeader
  |     +-- ConnectionIndicator
  +-- MainLayout
        +-- ChatPanel
        |     +-- MessageList
        |     |     +-- ChatMessage (repeated)
        |     |           +-- AgentBadge
        |     |           +-- MessageContent (markdown)
        |     |           +-- StructuredDataSummary
        |     |           +-- ViewDetailsButton
        |     |           +-- ExpandableReasoning
        |     +-- MessageInput
        +-- SidePanel
              +-- PhaseProgressBar
              +-- PanelContent (contextual)
              |     +-- CapacityTracker (default)
              |     |     +-- CapacityBar (repeated)
              |     |     +-- BottleneckLabel
              |     |     +-- DetailsTable (expandable)
              |     +-- ApprovalCard (on decision request)
              |     |     +-- OrderSummary
              |     |     +-- FunnelResults
              |     |     +-- RecommendationText
              |     |     +-- ActionButtons
              |     +-- DataDetailView (on "View details")
              |           +-- DataTable
              |           +-- CloseButton
              +-- AuditTrailSection (collapsible)
                    +-- AuditEntry (repeated)
```

## Component Specifications

### App
- Root component, initializes Zustand store and WebSocket connection
- Applies dark mode class based on system preference
- Renders AppHeader + MainLayout

### AppHeader
- App title: "DisruptionAI"
- ConnectionIndicator: shows "Reconnecting..." when status !== "connected"
- Minimal height, fixed at top

### ChatPanel
- Left side of MainLayout (flex: 1, takes remaining width)
- Contains MessageList (scrollable) + MessageInput (fixed bottom)

### MessageList
- Scrollable container with auto-scroll to bottom on new messages
- Renders ChatMessage components in chronological order
- `role="log"` and `aria-live="polite"` for accessibility

### ChatMessage
- Props: message (ChatMessage type)
- Renders AgentBadge if first message from this agent in sequence
- Renders markdown content with streaming cursor if `isStreaming`
- Renders StructuredDataSummary + ViewDetailsButton if `structuredData` present
- Renders ExpandableReasoning toggle if `expandableReasoning` present
- User messages: right-aligned, neutral background
- Assistant messages: left-aligned, agent-colored left border

### AgentBadge
- Props: agentName (string)
- Colored pill with agent name text
- Color mapped per BR-FE-03

### MessageInput
- Text input field with Send button
- Disabled when disconnected or agent is typing (BR-FE-01)
- Enter to send, Shift+Enter for newline
- Max length: 2000 chars
- `data-testid="chat-input-field"` and `data-testid="chat-send-btn"`

### SidePanel
- Right side of MainLayout (fixed width ~400px)
- Contains PhaseProgressBar (always visible) + PanelContent (contextual) + AuditTrailSection (collapsible)

### PhaseProgressBar
- Horizontal step indicator showing all workflow phases
- Current phase highlighted, completed phases checked, future dimmed
- Updated via `phase_update` ServerMessage
- `data-testid="phase-progress-bar"`

### CapacityTracker (default panel content)
- Progress bars per capacity dimension (BR-FE-06)
- Each CapacityBar: label, horizontal bar with fill color (green/yellow/red), percentage text
- BottleneckLabel below bars
- "Show details" toggle for numeric table
- `aria-valuenow`, `aria-valuemin`, `aria-valuemax` on each bar

### ApprovalCard (contextual panel content)
- Appears when `order_decision_request` arrives
- OrderSummary: order ID, product family, customer, priority, value, due date
- FunnelResults: 4 rows, each with layer name, pass/fail badge, detail text
- RecommendationText: agent recommendation with reasoning
- ActionButtons: Approve (green), Skip (yellow), Reject (red)
- Focus auto-moves to Approve button on card appearance
- All buttons have `aria-label` with order ID
- `data-testid` per BR-FE-13

### DataDetailView (contextual panel content)
- Full data table rendering for structured payloads
- Sortable columns for order tables
- Close button returns to previous panel mode
- `data-testid="detail-view-close-btn"`

### AuditTrailSection
- Collapsible section at bottom of side panel
- Toggle button: "Audit Trail (N entries)"
- Scrollable list of AuditEntry components (max 20 visible)
- Auto-scrolls to newest
- `data-testid="audit-trail-toggle"`

### AuditEntry
- Timestamp (relative), agent badge (small), action text
- Click to expand full details
- Compact single-line when collapsed

## API Integration Points

| Component | Backend Message | Direction |
|-----------|----------------|-----------|
| MessageInput | `user_message` ClientMessage | Client -> Server |
| ChatMessage | `stream_token` ServerMessage | Server -> Client |
| ChatMessage | `structured_data` ServerMessage | Server -> Client |
| AgentBadge | `agent_switch` ServerMessage | Server -> Client |
| ApprovalCard | `order_decision_request` ServerMessage | Server -> Client |
| ActionButtons | `order_decision` ClientMessage | Client -> Server |
| CapacityTracker | `capacity_update` ServerMessage | Server -> Client |
| PhaseProgressBar | `phase_update` ServerMessage | Server -> Client |
| AuditTrailSection | Embedded in `structured_data` (type=audit_trail) | Server -> Client |
| ConnectionIndicator | WebSocket connection events | Internal |
