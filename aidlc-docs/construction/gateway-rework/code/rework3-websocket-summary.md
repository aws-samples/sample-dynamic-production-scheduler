# Rework Cycle 3 — WebSocket Lambda Code Generation Summary

## Requirements Implemented
- REQ-F02 (phase progress): `detect_signals` parses stream tokens for phase keywords and emits `phase_update` messages
- REQ-F05 (agent status): `detect_signals` detects agent name patterns and emits `agent_switch` messages

## Implementation Details

### `detect_signals` function added to inline Lambda in `infrastructure/lib/websocket-stack.ts`

Signal detection logic:
- PHASE_KEYWORDS dict maps phrases ("impact assessment", "capacity analysis", etc.) to phase IDs
- AGENT_PATTERNS dict maps agent name strings to display names
- Rolling token_buffer (capped at 2000 chars) for context
- Emits `phase_update` and `agent_switch` WebSocket messages alongside `stream_token`

### Wiring
`detect_signals(decoded)` called in all 3 streaming code paths:
1. `text/event-stream` — after each `send_token(decoded, done=False)`
2. `application/json` — after `send_token(agent_reply, done=False)`
3. Fallback `else` — after `send_token(agent_reply, done=False)`

## Files Modified
| File | Change |
|------|--------|
| `infrastructure/lib/websocket-stack.ts` | Added detect_signals function + wired into 3 streaming paths |
