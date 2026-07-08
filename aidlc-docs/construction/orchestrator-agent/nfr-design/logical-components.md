# Logical Components — Unit 7: Orchestrator Agent

## Component Overview

```
Planner (Frontend)
      |
      | WebSocket message
      v
+-------------------------+
| Agent Entry Point       |  (fail-closed wrapper, Pattern 7)
+-------------------------+
      |
      v
+-------------------------+
| Strands Agent           |  (Claude 4.5 Haiku, system prompt)
+-------------------------+
      |
      +--------+--------+---------+
      |        |        |         |
      v        v        v         v
+--------+ +--------+ +--------+ +--------+
| Impact | | Capac. | | Constr | | Audit  |
| Agent  | | Agent  | | Agent  | | MCP    |
| Tool   | | Tool   | | Tool   | | Tool   |
+--------+ +--------+ +--------+ +--------+
      |        |        |         |
      v        v        v         v
+-------------------------+ +-------------+
| AgentCore Runtime API   | | AgentCore   |
| (sub-agent invocation)  | | Gateway     |
+-------------------------+ +-------------+
      |
      v
+-------------------------+
| Session Manager         |  (WorkflowSession + AgentCore Memory)
+-------------------------+
      |
      v
+-------------------------+
| Logging Layer           |  (JSON structured, Pattern 4)
+-------------------------+
      |
      v
+-------------------------+
| AgentCore Runtime       |  (hosting, scaling, lifecycle)
+-------------------------+
```

---

## Component 1: Agent Entry Point

- **Module**: `agent.py`
- **Responsibility**: Initialize Strands Agent, configure model, register tools, expose `run_agent()` wrapper
- **Pattern**: Fail-Closed Agent Wrapper (Pattern 7)
- **Startup sequence**:
  1. Load OrchestratorSettings from environment
  2. Configure structured logging
  3. Initialize BedrockModel (Claude 4.5 Haiku, max_tokens=8192, temp=0)
  4. Register sub-agent tools (invoke_impact_assessment, invoke_capacity_optimization, invoke_constraint_matching)
  5. Register MCP tools (write_audit_entry, get_audit_trail via Audit MCP)
  6. Register Python tools (session state helpers)
  7. Create Agent instance with system prompt

## Component 2: Agent Configuration

- **Module**: `config.py`
- **Responsibility**: Load and validate all agent settings from environment
- **Pattern**: Environment-Based Configuration (Pattern 5)
- **Validates at startup**:
  - All sub-agent IDs are non-empty
  - MCP Gateway URL is valid
  - Session timeout > 0
  - Retry limit >= 0
- **Fails fast**: If configuration invalid, agent exits with clear error

## Component 3: Session Manager

- **Module**: `session.py`
- **Responsibility**: WorkflowSession lifecycle, phase transitions, persistence
- **Pattern**: Hybrid Session State (Pattern 3)
- **Functions**:
  - `create_session()` — new WorkflowSession with UUID
  - `transition(new_phase)` — update phase, log transition
  - `record_decision(decision)` — append OrderDecision
  - `record_error(error)` — append AgentError
  - `persist(memory_client)` — write to AgentCore Memory
  - `restore(memory_client, session_id)` — read from AgentCore Memory

## Component 4: Sub-Agent Tools

- **Module**: `agent.py` (tool functions)
- **Responsibility**: Wrap AgentCore API calls as Strands `@tool` functions
- **Pattern**: Sub-Agent Failure with Partial Results (Pattern 2)
- **Tools**:
  - `invoke_impact_assessment(prompt)` — invoke Unit 4 via AgentCore API
  - `invoke_capacity_optimization(prompt)` — invoke Unit 5 via AgentCore API
  - `invoke_constraint_matching(prompt)` — invoke Unit 6 via AgentCore API
- Each tool: retry once on failure, return error string on permanent failure

## Component 5: Pydantic Schema Models

- **Module**: `models/schemas.py`
- **Responsibility**: Input/output validation for all Orchestrator data
- **Pattern**: Input Validation (Pattern 6)
- **Models**: OrchestratorConfig, WorkflowSession, WorkflowPhase, DisruptionEvent, SubAgentRequest, SubAgentResponse, OrderDecision, AgentError, StreamToken, StructuredPayload, OrchestratorAuditEntry, PlannerMessage, AgentResult

## Component 6: System Prompt

- **Module**: `prompts/system_prompt.py`
- **Responsibility**: Define Orchestrator persona, workflow instructions, tool usage, streaming rules
- **Contents**:
  - Agent role: "You are the DisruptionAI Orchestrator"
  - Workflow phases: disruption detection -> Round 1 -> Round 2 delays -> Round 2 funnel -> summary
  - Tool usage: when to invoke each sub-agent, what prompts to send
  - Planner interaction: always wait for confirmation, never decide for Planner
  - What-if handling: analyze question, route to affected agent(s)
  - Error handling: retry once, continue with partial results
  - Streaming rules: text pass-through, structured data as complete blocks
  - Summary format: structured plain-language summary

## Component 7: Structured Logger

- **Module**: `logging_config.py`
- **Responsibility**: JSON-formatted logging to stdout
- **Pattern**: Structured Agent Logging (Pattern 4)
- **Fields**: timestamp, level, agent_name, session_id, phase, duration_ms, message
- **Destination**: stdout (captured by AgentCore runtime to CloudWatch)

---

## Tool Registration

### Sub-Agent Tools (via AgentCore Runtime API)
| Tool | AgentCore Agent | Purpose |
|------|----------------|---------|
| invoke_impact_assessment | Unit 4 agent ID | Prioritize Florida orders |
| invoke_capacity_optimization | Unit 5 agent ID | Analyze capacity, manage delays |
| invoke_constraint_matching | Unit 6 agent ID | Run 4-layer constraint funnel |

### MCP Tools (via AgentCore Gateway HTTP/SSE)
| Tool | MCP Server | Purpose |
|------|-----------|---------|
| write_audit_entry | Audit MCP | Log workflow-level events |
| get_audit_trail | Audit MCP | Retrieve session audit history |

### Python Tools (local, registered with Strands)
| Tool | Module | Purpose |
|------|--------|---------|
| get_session_state | session.py | Return current WorkflowSession as text |
| update_session_phase | session.py | Transition to new workflow phase |

---

## Cross-Cutting Concerns

| Concern | Component | Pattern |
|---------|-----------|---------|
| LLM retry | Strands Agent | Exponential backoff (Pattern 1) |
| Sub-agent failure | Sub-Agent Tools | Retry + partial results (Pattern 2) |
| Session state | Session Manager | Hybrid state (Pattern 3) |
| Logging | Structured Logger | JSON middleware (Pattern 4) |
| Configuration | Agent Configuration | Environment variables (Pattern 5) |
| Input validation | Pydantic Models | Schema enforcement (Pattern 6) |
| Fail-closed | Agent Entry Point | Global wrapper (Pattern 7) |
| Streaming | System Prompt | Hybrid relay (Pattern 8) |

---

## Data Flow

```
1. Planner sends message via WebSocket
      |
      v
2. run_agent(message, session_id) -- fail-closed wrapper
      |
      v
3. Strands Agent processes message with system prompt context
      |
      v
4. LLM decides action:
   a) Disruption detected -> confirm with Planner
   b) Round 1 -> invoke_impact_assessment + invoke_capacity_optimization
   c) Round 2 delays -> invoke_capacity_optimization
   d) Round 2 funnel -> invoke_constraint_matching
   e) What-if -> re-invoke affected agent(s)
   f) Summary -> generate from conversation context
      |
      v
5. Sub-agent tool calls go through AgentCore Runtime API
      |
      v
6. Sub-agent responses streamed back through Orchestrator
      |
      v
7. Session state updated after each significant event
      |
      v
8. Audit entries written via Audit MCP
```
