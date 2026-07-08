# Rework Cycle 3 — Requirements Document

## Intent Analysis

- **User Request**: Implement live test feedback — fix backend agent failures and overhaul frontend UI
- **Request Type**: Enhancement + Bug Fix (hybrid)
- **Scope**: Multiple Components — 4 backend agents + orchestrator config + frontend SPA + WebSocket Lambda
- **Complexity**: Complex — backend concurrency/token fixes + major frontend UI overhaul with new interactive visualizations
- **Risk Level**: Medium — backend changes are targeted config/refactoring; frontend is significant new feature work

---

## Stream A: Backend Agent Fixes

### REQ-B01: Increase Sub-Agent Max Tokens
- **Current**: All 3 sub-agents (impact, capacity, constraint) use `max_tokens=4096`
- **Target**: Increase to `max_tokens=8192` for all 3 sub-agents
- **Rationale**: Large ERP payloads (20 orders + customers + equipment + materials + manpower) exhaust 4096 tokens mid-tool-call, causing `MaxTokensReachedException`
- **Files**: `impact-assessment-agent/agent.py`, `capacity-optimization-agent/agent.py`, `constraint-matching-agent/agent.py`

### REQ-B02: Fix Concurrency — New Agent Instances Per Invocation
- **Current**: Orchestrator reuses the same Strands Agent object for sub-agent calls, causing `ConcurrencyException` when retry fires while first invocation is still running
- **Target**: Create new agent instances per invocation instead of reusing a single instance
- **Rationale**: Strands Agent does not support concurrent invocations on the same object
- **Files**: `orchestrator-agent/agent.py` (sub-agent invocation logic)

### REQ-B03: Data Staging Tool Pattern
- **Current**: LLM must serialize large JSON payloads as tool input strings (e.g., `orders_json`), wasting tokens on format attempts
- **Target**: Add a data-preparation/staging tool that the agent calls first to stage fetched ERP data; scoring/funnel tools then read from staged state (no large JSON passing between LLM and tools)
- **Rationale**: Eliminates token waste from LLM struggling to format large JSON strings
- **Files**: All 3 sub-agent tool modules

### REQ-B04: Plant-Agnostic Parameter Naming
- **Current**: Tool parameters reference specific plants (e.g., `ohio_orders_json`, `florida_orders_json`)
- **Target**: Rename all plant-specific parameters to generic names (e.g., `receiving_plant_orders_json`, `disrupted_plant_orders_json`) and update system prompts to be direction-agnostic
- **Rationale**: Live test used "snowstorm in Ohio" (reversed from design assumption of Florida=disrupted). System should work for any plant disruption direction
- **Files**: Sub-agent tools, system prompts, funnel module

### REQ-B05: Retry Delay
- **Current**: `retry_limit=1` with no delay between retries
- **Target**: Keep `retry_limit=1` but add 30-second delay between retries
- **Rationale**: Gives first invocation time to complete before retry fires
- **Files**: `orchestrator-agent/agent.py` (retry logic)

### REQ-B06: Orchestrator Max Tokens Increase
- **Current**: Orchestrator uses Haiku with `max_tokens=8192`
- **Target**: Increase orchestrator `max_tokens` to `16384`
- **Rationale**: Complex multi-phase workflow needs more headroom; keep Haiku model (worked fine in live test)
- **Files**: `orchestrator-agent/config.py` or agent initialization

---

## Stream B: Frontend UI Overhaul

### REQ-F01: Fix Chat Message Rendering
- **Issue**: Tables from agents not rendering properly; long responses hard to scan
- **Target**:
  - Proper markdown table rendering with styled HTML tables
  - Collapsible sections for long agent responses (expand/collapse)
  - Visual distinction between orchestrator and sub-agent messages (color-coded badges, different background tints)
- **Files**: `ChatMessage.tsx`, `ChatPanel.tsx`

### REQ-F02: Fix Phase Progress Bar
- **Issue**: Never updated during live test — stayed on "idle"
- **Root Cause**: Orchestrator agent doesn't emit `phase_update` WebSocket messages; the WebSocket Lambda only forwards `stream_token` format
- **Target**:
  - Parse agent stream output for phase transition keywords and emit `phase_update` messages from WebSocket Lambda
  - OR: Have orchestrator explicitly send structured phase updates via audit MCP tool calls that the frontend can detect
  - Phase progress bar must update in real-time as workflow progresses through phases
- **Files**: `infrastructure/lib/websocket-stack.ts` (Lambda), `PhaseProgressBar.tsx`, `websocket.ts`, `store/index.ts`

### REQ-F03: Fix Capacity Tracker
- **Issue**: Never received data — always showed "Waiting for capacity data..."
- **Root Cause**: No `capacity_update` messages are emitted by the backend
- **Target**:
  - Extract capacity data from agent responses (capacity optimization agent output) and emit `capacity_update` messages
  - Capacity tracker must show real-time utilization across dimensions (Rolling Mill, Finishing Line, Material Tons, Operator Hours)
  - Color-coded thresholds (green/yellow/red)
- **Files**: `CapacityTracker.tsx`, `websocket-stack.ts`, `store/index.ts`

### REQ-F04: Fix Approval Card
- **Issue**: Never appeared — agent didn't send `order_decision_request` messages
- **Root Cause**: Orchestrator workflow doesn't emit structured `order_decision_request` messages for individual order decisions
- **Target**:
  - Detect order decision points in agent output and surface approval cards
  - OR: Implement as a post-analysis review panel where user can approve/reject/modify the agent's recommended order transfers
  - Approval card must show order details, funnel results, and approve/skip/reject buttons
- **Files**: `ApprovalCard.tsx`, `websocket-stack.ts`, `store/index.ts`

### REQ-F05: Real-Time Sub-Agent Status Indicators
- **New Feature**: Show which sub-agent is currently working
- **Target**:
  - Visual indicator in the side panel showing active sub-agent (impact assessment, capacity optimization, constraint matching)
  - Status transitions: idle → running → complete/failed
  - Parse agent stream for sub-agent invocation markers
- **Files**: New component `SubAgentStatus.tsx`, `SidePanel.tsx`, `store/index.ts`

### REQ-F06: Order Decision History Panel
- **New Feature**: Show all decisions made so far with running totals
- **Target**:
  - Panel showing list of orders with their transfer decisions (approve/skip/reject)
  - Running totals: orders transferred, capacity consumed, remaining capacity
  - Updated in real-time as decisions are made
- **Files**: New component `OrderHistory.tsx`, `SidePanel.tsx`, `store/index.ts`

### REQ-F07: Interactive Visualization Views
- **New Feature**: Rich interactive dashboards inspired by reference demos
- **Target**: Three visualization views accessible from the side panel:
  1. **Cascade Impact View**: Interactive visualization showing how disruption cascades through the supply chain — disrupted plant → affected orders → customer impact → downstream effects. Sankey-style or flow diagram showing order movement between plants
  2. **Scorecard View**: KPI scorecard dashboard showing procurement/operations alignment metrics — order fill rate, capacity utilization, customer tier coverage, transfer success rate. Gauge charts, progress bars, and metric cards
  3. **Transfer Flow View**: Interactive view of order transfers between plants — source plant, destination plant, order details, transfer status. Visual flow diagram or animated transfer indicators
- **Implementation**: Use a charting library (e.g., Recharts, which is React-friendly) for gauges, bar charts, Sankey diagrams
- **Files**: New components under `components/visualizations/`, `SidePanel.tsx`

### REQ-F08: Tablet Responsive Design
- **Target**: UI must work on tablet landscape orientation (no phone support needed)
- **Approach**: Responsive breakpoints for tablet landscape (1024px+), collapsible side panel on smaller viewports
- **Files**: All layout components, CSS/Tailwind adjustments

---

## Non-Functional Requirements

### NFR-01: Security Baseline
- All SECURITY rules enforced as blocking constraints (user confirmed A on Q7)
- Applies to both backend and frontend changes

### NFR-02: Performance
- Frontend visualizations must render within 500ms of data receipt
- WebSocket message parsing must not block UI thread
- Charting library must be tree-shakeable to minimize bundle size

### NFR-03: Maintainability
- New visualization components must be modular and reusable
- Data staging pattern in backend must be consistent across all 3 sub-agents
- Plant-agnostic naming must be applied consistently across all tools and prompts

---

## Security Compliance Summary

| Rule | Applicability | Status |
|------|--------------|--------|
| SECURITY-01 | N/A — no new data stores | N/A |
| SECURITY-02 | N/A — no new network intermediaries | N/A |
| SECURITY-03 | Applicable — agent logging changes | Must verify structured logging maintained |
| SECURITY-04 | Applicable — frontend changes | Must verify HTTP security headers maintained |
| SECURITY-05 | Applicable — tool interface changes | Must verify input validation on new tool interfaces |
| SECURITY-06 | N/A — no IAM changes | N/A |
| SECURITY-07 | N/A — no network config changes | N/A |
| SECURITY-08 | N/A — no auth changes | N/A |
| SECURITY-09 | Applicable — error handling changes | Must verify fail-closed patterns maintained |
| SECURITY-10 | Applicable — new frontend dependencies (charting lib) | Must pin versions, verify registry |
| SECURITY-11 | Applicable — data staging pattern | Must verify security isolation of staged data |
| SECURITY-12 | N/A — no auth mechanism changes | N/A |
| SECURITY-13 | N/A — no deserialization changes | N/A |
| SECURITY-14 | N/A — no alerting changes | N/A |
| SECURITY-15 | Applicable — new error paths in data staging | Must verify fail-closed on staging errors |
