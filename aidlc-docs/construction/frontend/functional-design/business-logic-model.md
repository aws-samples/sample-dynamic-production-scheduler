# Business Logic Model — Unit 8: Frontend

## UI Architecture Overview

```
+-------------------------------------------------------------------+
|                      DisruptionAI Frontend                        |
|                                                                   |
|  +-----------------------------+  +----------------------------+  |
|  |      Chat Panel (Left)      |  |   Side Panel (Right)       |  |
|  |                             |  |                            |  |
|  |  +------------------------+ |  |  +-----------------------+ |  |
|  |  | Message List           | |  |  | Phase Progress Bar    | |  |
|  |  | - Agent badges         | |  |  +-----------------------+ |  |
|  |  | - Streaming tokens     | |  |                            |  |
|  |  | - Inline summaries     | |  |  +-----------------------+ |  |
|  |  | - "View details" links | |  |  | Contextual Content    | |  |
|  |  +------------------------+ |  |  | (switches by context) | |  |
|  |                             |  |  |                       | |  |
|  |  +------------------------+ |  |  | Default: Capacity     | |  |
|  |  | Message Input          | |  |  |   Tracker             | |  |
|  |  | - Text field           | |  |  |                       | |  |
|  |  | - Send button          | |  |  | On decision request:  | |  |
|  |  | - Disabled when        | |  |  |   Approval Card       | |  |
|  |  |   disconnected         | |  |  |                       | |  |
|  |  +------------------------+ |  |  | On "View details":    | |  |
|  |                             |  |  |   Data Detail View    | |  |
|  +-----------------------------+  |  +-----------------------+ |  |
|                                   |                            |  |
|                                   |  +-----------------------+ |  |
|                                   |  | Audit Trail (bottom)  | |  |
|                                   |  +-----------------------+ |  |
|                                   +----------------------------+  |
+-------------------------------------------------------------------+
```

## 1. Chat Interface Logic

### Message Rendering Pipeline

1. Receive `stream_token` ServerMessage
2. Find or create ChatMessage by `messageId`
3. Append token to message content
4. If `done=true`: mark `isStreaming=false`, check for structured data
5. Render message with markdown support

### Agent Badge Logic

- When `agent_switch` ServerMessage arrives, update `activeAgent` in session state
- Display badge above current streaming message: "Impact Assessment Agent", "Capacity & Optimization Agent", "Constraint Matching Agent", "Orchestrator Agent"
- Badge color per agent (consistent throughout session)

### Structured Data Rendering

- When message has `structuredData`, render summary text in chat bubble
- Append "View details" button below summary
- On click: side panel switches to Data Detail View showing full table
- Supported types:
  - `order_table`: sortable table with order columns
  - `capacity_summary`: capacity dimensions with values
  - `delay_candidates`: delay candidate list with freed capacity
  - `funnel_result`: 4-layer pass/fail with reasoning
  - `audit_trail`: chronological audit entries

### Expandable Reasoning

- Messages with `expandableReasoning` show a "Show reasoning" toggle
- Collapsed by default
- On expand: renders reasoning text below the main message content
- Stays expanded until user collapses it

## 2. Side Panel Logic

### Panel Modes (Contextual Switching)

The side panel content area switches based on context:

| Trigger | Panel Content | Returns To |
|---------|--------------|------------|
| Default / no active context | Capacity Tracker | — |
| `order_decision_request` received | Approval Card | Capacity Tracker (after decision) |
| User clicks "View details" | Data Detail View | Previous view (on close) |

### Phase Progress Bar

- Always visible at top of side panel
- Shows current workflow phase from `WorkflowPhase` enum
- Phases displayed as horizontal step indicator
- Current phase highlighted, completed phases checked

### Approval Card Logic (Contextual)

Appears when backend sends `order_decision_request`:

1. Side panel content switches to Approval Card
2. Card displays:
   - Order summary (ID, product family, customer, priority, value)
   - 4-layer funnel results (pass/fail badges with detail text per layer)
   - Agent recommendation with reasoning
   - Three action buttons: Approve (green), Skip (yellow), Reject (red)
3. On button click:
   - Send `order_decision` ClientMessage via WebSocket
   - Disable buttons until next request arrives
   - Side panel returns to Capacity Tracker view
4. Buttons include `data-testid` attributes: `approval-card-approve-btn`, `approval-card-skip-btn`, `approval-card-reject-btn`

### Capacity Tracker Logic (Default View)

Displays running capacity state:

1. Progress bars per dimension (Rolling Mill, Finishing Line, Material, Operators)
2. Each bar shows: used / available with percentage
3. Color thresholds:
   - Green: < 70% utilized
   - Yellow: 70-89% utilized
   - Red: >= 90% utilized (threshold alert)
4. "Show details" toggle expands to full numeric table
5. Updated when `capacity_update` ServerMessage arrives
6. Shows bottleneck label below bars

### Audit Trail (Bottom Section)

- Collapsible section at bottom of side panel
- Shows most recent 10 audit entries (scrollable)
- Each entry: timestamp, agent badge, action, details
- Auto-scrolls to newest entry when updated

## 3. WebSocket Client Logic

### Connection Management

1. On app mount: connect to WebSocket URL (from env config)
2. Connection states: `connecting` | `connected` | `reconnecting` | `disconnected`
3. On successful connect: send session init message
4. On disconnect: begin auto-reconnect

### Auto-Reconnect (Exponential Backoff)

1. Initial delay: 1 second
2. Backoff multiplier: 2x
3. Max delay: 30 seconds
4. Max attempts: unlimited (keep trying)
5. Show subtle "Reconnecting..." indicator in header (not blocking)
6. On reconnect success: hide indicator, resume normal operation
7. No message replay (MVP simplicity)

### Message Dispatch

- Incoming ServerMessages dispatched to Zustand store actions by `type`
- Store actions update relevant state slices
- React components subscribe to specific slices (minimal re-renders)

## 4. State Management Model (Zustand)

### Store Shape

```
AppStore {
  // Session
  session: {
    sessionId: string | null
    currentPhase: WorkflowPhase
    activeAgent: string | null
  }

  // Connection
  connection: {
    status: "connecting" | "connected" | "reconnecting" | "disconnected"
    reconnectAttempt: number
  }

  // Chat
  chat: {
    messages: ChatMessage[]
    isAgentTyping: boolean
  }

  // Side Panel
  sidePanel: {
    mode: "tracker" | "approval" | "detail"
    pendingDecision: OrderDecisionRequest | null
    detailData: StructuredPayload | null
    previousMode: "tracker" | null
  }

  // Capacity
  capacity: CapacitySnapshot | null

  // Audit
  audit: {
    entries: AuditEntry[]
  }

  // Actions
  sendMessage(text: string): void
  sendDecision(orderId: string, decision: string, reason?: string): void
  appendStreamToken(messageId: string, token: string, done: boolean): void
  setPhase(phase: WorkflowPhase): void
  setActiveAgent(agent: string | null): void
  updateCapacity(snapshot: CapacitySnapshot): void
  setPendingDecision(request: OrderDecisionRequest | null): void
  showDetail(data: StructuredPayload): void
  closeDetail(): void
  addAuditEntry(entry: AuditEntry): void
}
```

### State Transitions

| Event | State Change |
|-------|-------------|
| WebSocket connected | connection.status = "connected" |
| WebSocket disconnected | connection.status = "reconnecting" |
| User sends message | Append user ChatMessage to chat.messages |
| stream_token received | Append token to matching message, set isAgentTyping |
| stream_token done=true | Mark message complete, clear isAgentTyping |
| structured_data received | Attach to current message |
| order_decision_request | sidePanel.mode = "approval", set pendingDecision |
| User clicks Approve/Skip/Reject | Send decision, sidePanel.mode = "tracker", clear pendingDecision |
| User clicks "View details" | sidePanel.mode = "detail", set detailData |
| User closes detail | sidePanel.mode = previousMode |
| capacity_update received | Update capacity snapshot |
| phase_update received | Update session.currentPhase |
| agent_switch received | Update session.activeAgent |

## 5. Dark Mode (System Preference)

- Detect OS preference via `prefers-color-scheme` media query
- Apply Tailwind `dark:` variants automatically
- No manual toggle in MVP
- Shadcn/ui components support dark mode natively via CSS variables
