# Rework Cycle 3 — Integration Test Instructions

## Purpose
Verify end-to-end flow from frontend through WebSocket to orchestrator and sub-agents after all Rework Cycle 3 changes.

## Prerequisites
- All 4 agents deployed and READY on AgentCore Runtime
- WebSocket Lambda deployed with `detect_signals` logic
- Frontend deployed to CloudFront

## Test 1: WebSocket E2E Smoke Test

Uses the existing `ws_test.py` script to verify the full pipeline.

```bash
/opt/homebrew/bin/python3.11 ws_test.py
```

### Expected Behavior
1. WebSocket connects to `wss://x5u9j1d0p7.execute-api.us-east-1.amazonaws.com/prod`
2. Sends disruption scenario message
3. Receives `stream_token` messages with agent response chunks
4. Stream completes with `done=true`
5. No `MaxTokensReachedException` errors (REQ-B01, REQ-B06)
6. No `ConcurrencyException` errors (REQ-B02)

### Verification Checklist
- [ ] Connection established successfully
- [ ] Agent responds with multi-phase analysis
- [ ] No token exhaustion errors in response
- [ ] Stream completes within 5 minutes
- [ ] Response includes impact assessment, capacity analysis, and constraint matching sections

## Test 2: Signal Detection Verification

After running ws_test.py, check CloudWatch logs for the WebSocket Lambda to verify signal detection is working.

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/disruptionai-ws-handler \
  --start-time $(date -v-10M +%s000) \
  --filter-pattern "phase_update" \
  --limit 20
```

### Expected Behavior
- Lambda logs show `phase_update` messages being sent for detected phases
- Lambda logs show `agent_switch` messages when sub-agents are invoked
- No errors in signal detection logic

## Test 3: Frontend Browser Integration

Open `https://d6o0q6xbaxa8j.cloudfront.net` in a browser.

### Manual Test Steps

1. Load the page — verify it renders without console errors
2. Type a disruption scenario in the chat input
3. Send the message and observe:
   - [ ] Chat messages render with proper markdown tables (REQ-F01)
   - [ ] Long responses have collapsible sections (REQ-F01)
   - [ ] Phase progress bar updates as workflow progresses (REQ-F02)
   - [ ] Sub-agent status indicators show active agent (REQ-F05)
   - [ ] Side panel tabs are navigable (Tracker/Agents/Orders/Visualizations)
4. Check visualization tabs:
   - [ ] Cascade Impact View renders (may show placeholder if no data yet)
   - [ ] Scorecard View renders
   - [ ] Transfer Flow View renders
5. Check responsive behavior:
   - [ ] Side panel collapses on narrower viewports
   - [ ] Layout works at 1024px+ width (tablet landscape)

## Test 4: Data Staging Pattern Verification

Verify sub-agents use the data staging pattern correctly by checking agent logs.

```bash
# Check impact assessment agent logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/disruptionai-ws-handler \
  --start-time $(date -v-10M +%s000) \
  --filter-pattern "stage_erp_data" \
  --limit 10
```

### Expected Behavior
- Sub-agents call `stage_erp_data` before scoring/funnel tools
- No large JSON payloads passed as tool input strings
- Scoring/funnel tools read from staged data successfully

## Test 5: Plant-Agnostic Scenario

Run a reversed disruption scenario to verify plant-agnostic naming (REQ-B04).

Connect via WebSocket and send:
```json
{
  "action": "sendMessage",
  "data": "A snowstorm has disrupted the Ohio plant. Assess impact on all active Ohio production orders."
}
```

### Expected Behavior
- Agent correctly identifies Ohio as the disrupted plant
- Constraint matching uses generic parameter names (receiving_plant, disrupted_plant)
- No hardcoded Florida/Ohio assumptions in agent responses

## Troubleshooting

### Agent Not Responding
1. Check agent status: `aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id orchestrator_agent-1YfV9m46l5`
2. Check WebSocket Lambda logs in CloudWatch
3. Verify `ORCHESTRATOR_AGENT_ARN` env var is set on the Lambda

### Token Exhaustion Errors
1. Verify `max_tokens` values in agent configs (8192 for sub-agents, 16384 for orchestrator)
2. Check if data staging pattern is being used (reduces token consumption)

### Concurrency Errors
1. Verify `agentcore_server.py` creates fresh Agent per invocation
2. Check for `_create_agent_per_request` pattern in orchestrator server
