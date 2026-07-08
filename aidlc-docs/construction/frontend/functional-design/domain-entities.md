# Domain Entities — Unit 8: Frontend

## Core Message Types

### ChatMessage
Represents a single message in the conversation thread.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique message ID (UUID) |
| role | "user" \| "assistant" | Who sent the message |
| content | string | Text content (may include markdown) |
| agentName | string \| null | Which agent generated this (null for user messages) |
| timestamp | string (ISO 8601) | When the message was created |
| isStreaming | boolean | Whether tokens are still arriving |
| structuredData | StructuredPayload \| null | Attached table/tracker data |
| expandableReasoning | string \| null | Collapsible "Explain reasoning" content |

### StreamToken
A single token received during streaming.

| Field | Type | Description |
|-------|------|-------------|
| messageId | string | Which message this token belongs to |
| token | string | The text fragment |
| done | boolean | Whether this is the final token |

### StructuredPayload
Structured data attached to a message (tables, capacity summaries).

| Field | Type | Description |
|-------|------|-------------|
| type | "order_table" \| "capacity_summary" \| "delay_candidates" \| "funnel_result" \| "audit_trail" | Payload type |
| title | string | Display title |
| data | object | Type-specific data (see below) |

---

## Order & Priority Types

### ProductionOrder
Frontend representation of a production order.

| Field | Type | Description |
|-------|------|-------------|
| orderId | string | e.g., "PO-2026-001" |
| plant | "Florida" \| "Ohio" | Source plant |
| productFamily | string | Steel Sheets / Coils / Plates / Bars |
| quantity | number | Units |
| dueDate | string (ISO date) | Customer deadline |
| customerName | string | Customer display name |
| customerTier | "Tier1" \| "Tier2" \| "Tier3" | Customer tier |
| orderValue | number | Dollar amount |
| priority | "P1" \| "P2" \| "P3" \| null | Assigned priority (null before classification) |
| status | string | Active / Delayed / Transferred / Cancelled |

### OrderDecisionRequest
Sent by backend when an order needs Planner approval.

| Field | Type | Description |
|-------|------|-------------|
| orderId | string | Order requiring decision |
| order | ProductionOrder | Full order details |
| recommendation | "transfer" \| "transfer_with_procurement" \| "transfer_overtime" \| "non_transferable" | Agent recommendation |
| funnelResults | FunnelLayerResult[] | 4-layer constraint results |
| reasoning | string | Agent explanation |

### FunnelLayerResult
Result of one constraint funnel layer.

| Field | Type | Description |
|-------|------|-------------|
| layer | 1 \| 2 \| 3 \| 4 | Layer number |
| name | "Equipment" \| "Material" \| "Utilization" \| "Cascade" | Layer name |
| passed | boolean | Whether the order passed this layer |
| detail | string | Explanation text |

### OrderDecisionResponse
Planner's decision on an order.

| Field | Type | Description |
|-------|------|-------------|
| orderId | string | Order ID |
| decision | "approve" \| "skip" \| "reject" | Planner decision |
| reason | string \| null | Optional reason for reject/skip |

---

## Capacity Tracker Types

### CapacitySnapshot
Running capacity tracker state displayed in side panel.

| Field | Type | Description |
|-------|------|-------------|
| rollingMill | CapacityDimension | Rolling Mill hours |
| finishingLine | CapacityDimension | Finishing Line hours |
| materialTons | CapacityDimension | Raw material tons |
| operatorHours | CapacityDimension | Operator hours |
| bottleneck | string | Current bottleneck description |
| lastUpdated | string (ISO 8601) | When tracker was last updated |

### CapacityDimension
A single capacity dimension with used/available tracking.

| Field | Type | Description |
|-------|------|-------------|
| label | string | Display label (e.g., "Rolling Mill") |
| used | number | Currently consumed |
| available | number | Total available |
| unit | string | Unit label (e.g., "hours", "tons") |
| thresholdPct | number | Alert threshold (default 90) |

---

## Session & Connection Types

### WorkflowSession
Frontend session state.

| Field | Type | Description |
|-------|------|-------------|
| sessionId | string | Backend session ID |
| currentPhase | WorkflowPhase | Current workflow phase |
| isConnected | boolean | WebSocket connection status |
| activeAgent | string \| null | Currently active agent name |

### WorkflowPhase
Enum of workflow phases for progress display.

Values: "idle" | "disruption_intake" | "impact_assessment" | "capacity_analysis" | "delay_optimization" | "constraint_matching" | "what_if" | "summary" | "complete"

---

## Audit Types

### AuditEntry
A single audit trail entry.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Entry ID |
| timestamp | string (ISO 8601) | When the action occurred |
| agent | string | Which agent performed the action |
| action | string | What was done |
| details | string | Human-readable description |
| sessionId | string | Session this belongs to |

---

## WebSocket Message Types

### ClientMessage (client-to-server)

| Field | Type | Description |
|-------|------|-------------|
| type | "user_message" \| "order_decision" \| "constraint_input" | Message type |
| sessionId | string | Session ID |
| payload | object | Type-specific payload |

#### user_message payload
| Field | Type |
|-------|------|
| text | string |

#### order_decision payload
| Field | Type |
|-------|------|
| orderId | string |
| decision | "approve" \| "skip" \| "reject" |
| reason | string \| null |

#### constraint_input payload
| Field | Type |
|-------|------|
| constraint | string |

### ServerMessage (server-to-client)

| Field | Type | Description |
|-------|------|-------------|
| type | "stream_token" \| "structured_data" \| "order_decision_request" \| "phase_update" \| "capacity_update" \| "agent_switch" \| "error" | Message type |
| sessionId | string | Session ID |
| payload | object | Type-specific payload (matches domain entities above) |
