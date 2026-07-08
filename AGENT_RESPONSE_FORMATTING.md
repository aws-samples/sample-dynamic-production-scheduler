# Agent Response Formatting Implementation

## Overview
Implemented three solutions to format and display agent responses on the AI Assistant page using the `disruptionai-tracker` DynamoDB table.

## 1. Capacity Tracker Panel Component

**File**: `frontend-spa/src/components/chat/CapacityTrackerPanel.tsx`

**Features**:
- Real-time capacity monitoring with 5-second polling
- Visual progress bars for machine capacity (Rolling Mill, Finishing Line)
- Material inventory display
- Workforce availability
- Order decision counters (approved/delayed/rejected)
- Auto-updates as decisions are made

**Display**:
- Machine hours broken down by shift tier (Normal, Overtime, Weekend)
- Color-coded progress bars (blue for Rolling Mill, purple for Finishing Line)
- Material surplus by type (Steel Coils, Sheets, Plates)
- Decision badges with icons (green checkmark, yellow clock, red X)

## 2. Formatted Agent Response Component

**File**: `frontend-spa/src/components/chat/FormattedAgentResponse.tsx`

**Features**:
- Extracts structured data from nondeterministic markdown text
- Parses order IDs (PO-YYYY-NNN format)
- Identifies recommendations and their categories
- Detects decisions (APPROVED, REJECTED, SKIPPED)
- Extracts capacity metrics (hours, tons, operators)

**Display**:
- Structured cards for decisions with color-coded badges
- Recommendation summaries with category indicators
- Capacity metrics grid for Capacity Optimization agent
- Falls back to plain markdown if no structured data found

**Extraction Patterns**:
- Order IDs: `/PO-\d{4}-\d{3}/g`
- Recommendations: `/(PO-\d{4}-\d{3}).*?(Transfer|Non-transferable|...)/gi`
- Decisions: `/(PO-\d{4}-\d{3}).*?(APPROVED|REJECTED|SKIPPED)/gi`
- Capacity: `/(\d+\.?\d*)\s*(hrs?|hours?|tons?|operators?)/gi`

## 3. Integration with Chat Panel

**Updated Files**:
- `frontend-spa/src/components/chat/ChatMessage.tsx` - Uses FormattedAgentResponse for agent messages
- `frontend-spa/src/components/chat/ChatPanel.tsx` - Includes CapacityTrackerPanel
- `infrastructure/rest-proxy/index.py` - Added tracker API endpoint

**API Endpoint**:
```json
POST /api
{
  "action": "tracker",
  "sessionId": "disruptionai-session-id"
}
```

**Response**:
```json
{
  "session_id": "string",
  "rolling_mill_normal_hrs": number,
  "rolling_mill_overtime_hrs": number,
  "rolling_mill_weekend_hrs": number,
  "finishing_line_normal_hrs": number,
  "finishing_line_overtime_hrs": number,
  "finishing_line_weekend_hrs": number,
  "material_surplus_tons": {
    "Steel Coils": number,
    "Steel Sheets": number,
    "Steel Plates": number
  },
  "workforce_surplus": number,
  "orders_transferred": ["PO-2026-001", ...],
  "orders_delayed": ["PO-2026-021", ...],
  "orders_rejected": ["PO-2026-030", ...],
  "last_updated": "ISO timestamp"
}
```

## DynamoDB Table Schema

**Table**: `disruptionai-tracker`

**Primary Key**: `session_id` (String)

**Attributes**:
- Machine capacity (normal, overtime, weekend hours)
- Material inventory by type
- Workforce availability
- Order decision lists (transferred, delayed, rejected)
- Last updated timestamp

## How It Works

1. **During Constraint Funnel**:
   - Agent makes recommendations for each order
   - User approves/rejects/skips orders
   - Constraint Matching Agent updates tracker in DynamoDB
   - Capacity is decremented in real-time

2. **On AI Assistant Page**:
   - CapacityTrackerPanel polls tracker endpoint every 5 seconds
   - Displays current capacity state with visual indicators
   - Shows decision counts and progress

3. **In Chat Messages**:
   - FormattedAgentResponse parses agent text
   - Extracts structured data (orders, decisions, metrics)
   - Displays formatted cards alongside markdown
   - Color-codes recommendations and decisions

## Benefits

1. **Real-time Visibility**: See capacity changes as decisions are made
2. **Structured Display**: Extract key information from unstructured text
3. **Better UX**: Visual progress bars and color-coded badges
4. **Persistent State**: Tracker survives across agent invocations
5. **No Agent Changes**: Works with existing nondeterministic responses

## Testing

To test the implementation:

1. Start a disruption workflow
2. Navigate to AI Assistant page
3. Proceed to constraint funnel phase
4. Make order decisions (approve/reject/skip)
5. Watch the tracker panel update in real-time
6. Observe formatted decision cards in chat messages

## Future Enhancements

- Add historical capacity charts
- Show capacity forecast based on pending orders
- Add alerts when capacity thresholds are reached
- Export tracker data to CSV
- Add capacity comparison across sessions
