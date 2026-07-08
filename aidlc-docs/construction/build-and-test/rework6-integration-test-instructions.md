# Integration Test Instructions — Rework 6

## Purpose
Verify the end-to-end response pipeline: orchestrator → AgentCore → Lambda proxy → browser.

## Test Scenario 1: `update_ui` Tool → Envelope Construction

### Setup
```bash
cd orchestrator-agent
python
```

### Test Script
```python
from orchestrator_agent.agent import update_ui, _reset_ui_accumulator, _get_ui_payloads

# Simulate a Round 1 complete scenario
_reset_ui_accumulator()
update_ui.__wrapped__(
    phase="round1_complete",
    orders=[{"orderId": "PO-1001", "product": "Steel Coil", "priority": "P1"}],
    capacity={"rollingMill": 72, "finishingLine": 85, "rawMaterial": 60, "manpower": 45},
    priorities={"P1": 5, "P2": 3, "P3": 7, "P1Value": "$1.2M", "P2Value": "$800K", "P3Value": "$450K"},
    totalOrders=15,
    totalValue="$2,450,000",
    bottleneck="Rolling Mill",
)

payloads = _get_ui_payloads()
assert len(payloads) == 1
assert payloads[0]["phase"] == "round1_complete"
assert len(payloads[0]["orders"]) == 1
assert payloads[0]["capacity"]["rollingMill"] == 72
print("PASS: update_ui tool produces valid payload")
```

## Test Scenario 2: Lambda Proxy Envelope Passthrough

### Prerequisites
- Lambda deployed with updated `index.mjs`
- Agent deployed with `update_ui` tool

### Test
```bash
# Send a test message and verify the response contains the ui field
curl -X POST https://<API_URL> \
  -H "Content-Type: application/json" \
  -d '{"message": "A hurricane is affecting the Florida plant. Begin disruption response.", "sessionId": "test-rework6-integration"}' \
  | python -m json.tool
```

### Expected Response Shape
```json
{
  "result": "I understand a hurricane is affecting the Florida plant...",
  "ui": {
    "phase": "confirmation"
  },
  "session_id": "test-rework6-integration"
}
```

### Verify
1. Response is valid JSON (not SSE)
2. `ui` field is present and non-empty
3. `ui.phase` matches the expected workflow phase
4. `result` contains the LLM's text response (no JSON blocks embedded)
5. `X-Session-Id` header matches `session_id` in body

## Test Scenario 3: Frontend Rendering from uiData

### Prerequisites
- Frontend deployed with rework6 changes
- Backend pipeline working (Scenarios 1-2 pass)

### Manual Test Steps
1. Open the frontend at the CloudFront URL
2. Navigate to Disruption page
3. Select a plant and start a disruption
4. Verify Round 1 results render in the structured card (not raw markdown)
5. Verify delay candidates appear as cards with Approve/Reject buttons
6. Verify constraint funnel orders appear with decision buttons
7. Verify the Kanban board updates as decisions are made
8. Verify the summary phase completes the workflow

### What to Check
- No raw JSON blocks visible in the chat
- Structured data (orders, capacity, priorities) renders in UI components
- Approval buttons work and send decisions back to the orchestrator
- Phase transitions happen automatically based on `uiData.phase`
