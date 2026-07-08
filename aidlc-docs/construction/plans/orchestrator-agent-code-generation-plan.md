# Code Generation Plan — Unit 7: Orchestrator Agent

## Unit Context

- **Unit**: Orchestrator Agent — top-level coordinator for DisruptionAI workflow
- **Stories**: US-01 (disruption detection), US-02 (Round 1), US-03 (Round 2 delays), US-04 (Round 2 funnel), US-05 (what-if), US-06 (summary)
- **Dependencies**: Units 4, 5, 6 (sub-agents via AgentCore API), Unit 3 (Audit MCP via Gateway)
- **Pattern Reference**: Unit 4 (impact-assessment-agent) — same framework, same hosting model
- **Key Difference**: Orchestrator has sub-agent tools (AgentCore invoke) instead of scoring tools, plus session state management

## Code Location

- **Application Code**: `orchestrator-agent/` (workspace root)
- **Documentation**: `aidlc-docs/construction/orchestrator-agent/code/`

## Generation Steps

### Step 1: Project Structure Setup
- [x] Create `orchestrator-agent/pyproject.toml` (build-backend: setuptools.build_meta)
- [x] Create `orchestrator-agent/src/orchestrator_agent/__init__.py`
- [x] Create `orchestrator-agent/src/orchestrator_agent/models/__init__.py`
- [x] Create `orchestrator-agent/src/orchestrator_agent/prompts/__init__.py`
- [x] Create `orchestrator-agent/tests/__init__.py`

### Step 2: Pydantic Schema Models
- [x] Create `orchestrator-agent/src/orchestrator_agent/models/schemas.py`
- [x] Models: WorkflowPhase (enum), DisruptionEvent, SubAgentRequest, SubAgentResponse, OrderDecision, AgentError, StreamToken, StructuredPayload, OrchestratorAuditEntry, PlannerMessage (with sanitization), AgentResult
- [x] Source: domain-entities.md + Pattern 6 (input validation)

### Step 3: Schema Unit Tests
- [x] Create `orchestrator-agent/tests/test_schemas.py`
- [x] Test: WorkflowPhase enum values, PlannerMessage validation (max length, empty, sanitization), DisruptionEvent construction, OrderDecision construction, AgentError construction, AgentResult construction

### Step 4: Configuration Module
- [x] Create `orchestrator-agent/src/orchestrator_agent/config.py`
- [x] OrchestratorSettings (pydantic-settings BaseSettings) with all env vars from tech-stack-decisions.md
- [x] Startup validation: sub-agent IDs non-empty, session_timeout > 0, retry_limit >= 0
- [x] Source: Pattern 5 (env config)

### Step 5: Configuration Unit Tests
- [x] Create `orchestrator-agent/tests/test_config.py`
- [x] Test: default values, env override, validation failures (empty agent ID, invalid timeout)

### Step 6: Logging Module
- [x] Create `orchestrator-agent/src/orchestrator_agent/logging_config.py`
- [x] JSON structured logging to stdout, same pattern as Unit 4
- [x] Source: Pattern 4 (structured logging)

### Step 7: Session Manager
- [x] Create `orchestrator-agent/src/orchestrator_agent/session.py`
- [x] WorkflowSession dataclass with: create_session(), transition(), record_decision(), record_error(), to_dict(), from_dict()
- [x] Phase transition validation (valid state machine transitions)
- [x] Source: Pattern 3 (hybrid session state), domain-entities.md

### Step 8: Session Unit Tests
- [x] Create `orchestrator-agent/tests/test_session.py`
- [x] Test: create_session, phase transitions (valid + invalid), record_decision, record_error, to_dict/from_dict round-trip

### Step 9: System Prompt
- [x] Create `orchestrator-agent/src/orchestrator_agent/prompts/system_prompt.py`
- [x] get_system_prompt() function returning the full Orchestrator system prompt
- [x] Content: role definition, workflow phases, tool usage instructions, Planner interaction rules, what-if handling, error handling, streaming rules, summary format
- [x] Source: business-logic-model.md (6 phases), business-rules.md (BR-OA-01 through BR-OA-15), Pattern 8 (streaming)

### Step 10: Agent Module
- [x] Create `orchestrator-agent/src/orchestrator_agent/agent.py`
- [x] Sub-agent tool functions: invoke_impact_assessment, invoke_capacity_optimization, invoke_constraint_matching (each with retry + partial results per Pattern 2)
- [x] Session tools: get_session_state, update_session_phase (registered as @tool)
- [x] MCP client factory: _create_mcp_client() for Audit MCP via mcp-proxy-for-aws
- [x] Agent factory: create_agent(settings) -> Agent
- [x] Fail-closed wrapper: run_agent(agent, task, session_id) -> AgentResult (Pattern 7)
- [x] Source: Unit 4 agent.py pattern, logical-components.md, nfr-design-patterns.md

### Step 11: Agent Unit Tests
- [x] Create `orchestrator-agent/tests/test_agent.py`
- [x] Test: sub-agent tool functions (mock AgentCore client — success, retry, permanent failure), session tools (get_session_state, update_session_phase), run_agent wrapper (success, exception -> AgentResult error), create_agent initialization

### Step 12: README
- [x] Create `orchestrator-agent/README.md`
- [x] Overview, project structure, environment variables, dependencies, running tests, deployment

### Step 13: Code Generation Summary
- [x] Create `aidlc-docs/construction/orchestrator-agent/code/code-generation-summary.md`
- [x] List all files created, test counts, story coverage, SECURITY compliance

## Story Traceability

| Story | Covered By |
|-------|-----------|
| US-01 (Disruption Detection) | system_prompt.py (Phase 1 instructions), schemas.py (DisruptionEvent) |
| US-02 (Round 1) | system_prompt.py (Phase 2), agent.py (invoke_impact_assessment, invoke_capacity_optimization) |
| US-03 (Round 2 Delays) | system_prompt.py (Phase 3), agent.py (invoke_capacity_optimization) |
| US-04 (Round 2 Funnel) | system_prompt.py (Phase 4), agent.py (invoke_constraint_matching) |
| US-05 (What-If) | system_prompt.py (Phase 5), agent.py (all sub-agent tools) |
| US-06 (Summary) | system_prompt.py (Phase 6), session.py (decisions tracking) |

## Total Steps: 13
