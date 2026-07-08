# Rework Cycle 3 — Code Generation Plan

## Overview
Three parallel streams implementing 14 requirements from live test feedback.

---

## Stream A: Backend Agent Fixes (REQ-B01 through REQ-B06)

### Step A1: Increase sub-agent max_tokens (REQ-B01)
- [x] `impact-assessment-agent/src/impact_assessment_agent/agent.py` — change `max_tokens=4096` to `max_tokens=8192`
- [x] `capacity-optimization-agent/src/capacity_optimization_agent/agent.py` — change `max_tokens=4096` to `max_tokens=8192`
- [x] `constraint-matching-agent/src/constraint_matching_agent/agent.py` — change `max_tokens=4096` to `max_tokens=8192`

### Step A2: Increase orchestrator max_tokens (REQ-B06)
- [x] `orchestrator-agent/src/orchestrator_agent/agent.py` — change `max_tokens=8192` to `max_tokens=16384`

### Step A3: Add retry delay (REQ-B05)
- [x] `orchestrator-agent/src/orchestrator_agent/config.py` — add `retry_delay_seconds: int = 30`
- [x] `orchestrator-agent/src/orchestrator_agent/agent.py` — add `time.sleep(settings.retry_delay_seconds)` before retry in `_invoke_sub_agent`

### Step A4: Fix concurrency — new agent instances per invocation (REQ-B02)
- [x] `orchestrator-agent/src/orchestrator_agent/agentcore_server.py` — refactored to create fresh Agent per invocation while caching settings/MCP client. Replaced `_get_agent()` singleton with `_create_agent_per_request()` factory.

### Step A5: Add data staging tool pattern (REQ-B03)
- [x] `impact-assessment-agent/src/impact_assessment_agent/agent.py` — add `stage_erp_data` tool that stores fetched data in module-level dict; refactor `score_orders_tool` to read from staged data instead of requiring JSON string params
- [x] `capacity-optimization-agent/src/capacity_optimization_agent/agent.py` — add `stage_erp_data` tool; refactor `compute_capacity_snapshot` to read from staged data
- [x] `constraint-matching-agent/src/constraint_matching_agent/agent.py` — add `stage_erp_data` tool; refactor `evaluate_funnel_tool` to read from staged data

### Step A6: Plant-agnostic parameter naming (REQ-B04)
- [x] `constraint-matching-agent/src/constraint_matching_agent/agent.py` — rename `ohio_orders_json` to `receiving_plant_orders_json` in `evaluate_funnel_tool` and `simulate_cascade_tool`
- [x] Update all 3 system prompts to use generic plant references (disrupted plant / receiving plant) instead of Florida/Ohio

### Step A7: Backend code generation summary
- [x] Create `aidlc-docs/construction/gateway-rework/code/rework3-backend-summary.md`

---

## Stream B: Frontend UI Overhaul (REQ-F01 through REQ-F08)

### Step B1: Add recharts + remark-gfm dependencies (REQ-F07)
- [x] Update `frontend-spa/package.json` — add `recharts` and `remark-gfm` (for table rendering)

### Step B2: Enhance markdown rendering with GFM tables (REQ-F01)
- [x] `frontend-spa/src/lib/markdown.tsx` — add `remark-gfm` plugin for proper table rendering, add custom table/th/td components with styled classes

### Step B3: Enhance ChatMessage with collapsible sections and agent badges (REQ-F01)
- [x] `frontend-spa/src/components/chat/ChatMessage.tsx` — add collapsible long content, agent-specific background tints

### Step B4: Update TypeScript types (REQ-F01–F08)
- [x] `frontend-spa/src/types/index.ts` — add `SubAgentInfo`, `OrderDecision`, expand `SidePanelMode` with new tab values, add visualization data types

### Step B5: Update Zustand store (REQ-F02–F06)
- [x] `frontend-spa/src/store/index.ts` — add `subAgents` state slice, `orderHistory` slice, new actions for phase parsing, agent status, order decisions

### Step B6: Update WebSocket client message handling (REQ-F02–F05)
- [x] `frontend-spa/src/lib/websocket.ts` — handle new message types: `phase_update`, `capacity_update`, `order_decision`, `agent_switch`

### Step B7: Fix PhaseProgressBar to parse stream (REQ-F02)
- [x] `frontend-spa/src/components/side/PhaseProgressBar.tsx` — already wired to store phase; store now receives phase updates via WebSocket Lambda signal detection

### Step B8: Create SubAgentStatus component (REQ-F05)
- [x] Create `frontend-spa/src/components/side/SubAgentStatus.tsx`

### Step B9: Create OrderHistory component (REQ-F06)
- [x] Create `frontend-spa/src/components/side/OrderHistory.tsx`

### Step B10: Create visualization components (REQ-F07)
- [x] Create `frontend-spa/src/components/visualizations/CascadeImpactView.tsx`
- [x] Create `frontend-spa/src/components/visualizations/ScorecardView.tsx`
- [x] Create `frontend-spa/src/components/visualizations/TransferFlowView.tsx`

### Step B11: Update SidePanel with tab navigation (REQ-F05–F07)
- [x] `frontend-spa/src/components/side/SidePanel.tsx` — add tab bar for Tracker/Agents/Orders/Visualizations
- [x] `frontend-spa/src/components/side/PanelContent.tsx` — route new tab modes

### Step B12: Tablet responsive adjustments (REQ-F08)
- [x] Review layout components for 1024px+ breakpoint; add collapsible side panel toggle

### Step B13: Frontend code generation summary
- [x] Create `aidlc-docs/construction/gateway-rework/code/rework3-frontend-summary.md`

---

## Stream C: WebSocket Lambda Updates (REQ-F02, F03, F04, F05)

### Step C1: Add stream parsing to WebSocket Lambda
- [x] `infrastructure/lib/websocket-stack.ts` — enhanced inline Lambda with `detect_signals` function: phase keyword detection (PHASE_KEYWORDS dict), agent switch detection (AGENT_PATTERNS dict), buffer management. Wired `detect_signals(decoded)` call into all 3 streaming code paths (text/event-stream, application/json, fallback). Emits `phase_update` and `agent_switch` structured messages alongside `stream_token`.

### Step C2: WebSocket code generation summary
- [x] Create `aidlc-docs/construction/gateway-rework/code/rework3-websocket-summary.md`

---

## Final Steps

### Step F1: Update aidlc-state.md
- [x] Mark all 3 streams complete

### Step F2: Present completion message
- [x] Present standardized completion message with file list
