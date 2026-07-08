# Deployment Architecture — Unit 7: Orchestrator Agent

## Deployment Model

The Orchestrator Agent is hosted on Bedrock AgentCore managed runtime. AgentCore handles scaling, health checks, and lifecycle. The agent invokes three sub-agents (also on AgentCore) via the AgentCore API.

```
+-----------------------------------------------------------+
|  Bedrock AgentCore Managed Runtime                        |
|                                                           |
|  +-----------------------------------------------------+ |
|  | Orchestrator Agent (Python 3.11)                     | |
|  |                                                     | |
|  | - Strands Agents SDK                                | |
|  | - Claude 4.5 Haiku (Bedrock)                        | |
|  | - Sub-agent tools (AgentCore invoke)                 | |
|  | - Session manager (WorkflowSession)                 | |
|  | - Pydantic validation                               | |
|  | - JSON structured logging                           | |
|  +-----------------------------------------------------+ |
|       |              |              |                      |
|       | InvokeModel  | InvokeAgent  | HTTP/SSE             |
|       v              v              v                      |
|  +----------+ +-------------+ +-----------------+          |
|  | Claude   | | Sub-Agents  | | AgentCore       |          |
|  | 4.5      | | (Units 4-6) | | Gateway         |          |
|  | Haiku    | | on AgentCore| | +-----+         |          |
|  +----------+ +-------------+ | | Aud |         |          |
|                               | | MCP |         |          |
|                               | +-----+         |          |
|                               +-----------------+          |
|       |                                                    |
|       | AgentCore Memory API                               |
|       v                                                    |
|  +-----------------------------------------------------+  |
|  | AgentCore Memory (shared context)                    |  |
|  | Keys: workflow_session, prioritized_orders,          |  |
|  |       capacity_snapshot                              |  |
|  +-----------------------------------------------------+  |
+-----------------------------------------------------------+
```

## Communication Paths

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| Frontend (WebSocket) | Orchestrator Agent | AgentCore invoke | Planner messages |
| Orchestrator | Claude 4.5 Haiku | Bedrock API (HTTPS) | LLM reasoning |
| Orchestrator | Impact Assessment Agent | AgentCore invoke | Round 1 classification |
| Orchestrator | Capacity Optimization Agent | AgentCore invoke | Round 1 capacity + Round 2 delays |
| Orchestrator | Constraint Matching Agent | AgentCore invoke | Round 2 funnel |
| Orchestrator | Audit MCP | HTTP/SSE via Gateway | Workflow audit entries |
| Orchestrator | AgentCore Memory | AgentCore API | Session + shared context |

## Environment Variables

Injected via AgentCore agent configuration at deployment time.

| Variable | Example Value | Purpose |
|----------|--------------|---------|
| BEDROCK_MODEL_ID | us.anthropic.claude-4-5-haiku-20250514-v1:0 | LLM model |
| MCP_GATEWAY_URL | https://agentcore-gateway.us-east-1.amazonaws.com | Gateway endpoint |
| IMPACT_ASSESSMENT_AGENT_ID | agent-id-unit4 | Sub-agent ID |
| CAPACITY_OPTIMIZATION_AGENT_ID | agent-id-unit5 | Sub-agent ID |
| CONSTRAINT_MATCHING_AGENT_ID | agent-id-unit6 | Sub-agent ID |
| AUDIT_MCP_URL | https://agentcore-gateway.../audit-mcp | Audit MCP endpoint |
| SESSION_TIMEOUT_MINUTES | 60 | Session inactivity timeout |
| MAX_TURNS | 100 | Max LLM turns per session |
| RETRY_LIMIT | 1 | Sub-agent retry count |
| LOG_LEVEL | INFO | Logging verbosity |

No secrets or credentials in environment variables. Authentication via IAM role.

---

## Packaging and Deployment

### Package Structure

```
orchestrator-agent/
  src/
    orchestrator_agent/
      __init__.py
      agent.py
      config.py
      session.py
      models/schemas.py
      prompts/system_prompt.py
      logging_config.py
  tests/
  pyproject.toml
  README.md
```

### Deployment Steps

1. Package agent code as a zip or directory artifact
2. Register agent with AgentCore via CDK (Unit 9)
3. AgentCore installs dependencies from pyproject.toml
4. AgentCore starts agent entry point on invocation
5. Sub-agent IDs injected as environment variables (depends on Units 4-6 being registered first)

### Deployment Order

The Orchestrator depends on sub-agents being registered first:
1. Unit 1: ERP Data MCP (AgentCore Gateway)
2. Unit 3: Audit MCP (AgentCore Gateway)
3. Unit 4: Impact Assessment Agent (AgentCore)
4. Unit 5: Capacity & Optimization Agent (AgentCore)
5. Unit 6: Constraint Matching Agent (AgentCore)
6. Unit 7: Orchestrator Agent (AgentCore) — depends on 4, 5, 6

---

## Process Lifecycle

| Event | Behavior |
|-------|----------|
| Agent invoked | AgentCore starts Python process, loads agent module |
| Request received | Agent processes Planner message via Strands SDK |
| Sub-agent call | Agent calls AgentCore InvokeAgent API for sub-agent |
| MCP tool call | Agent calls Gateway endpoint (HTTP/SSE) for Audit MCP |
| LLM call | Strands SDK calls Bedrock InvokeModel for Claude 4.5 Haiku |
| Completion | Agent returns result, AgentCore manages process cleanup |
| Error | Fail-closed wrapper catches exceptions, returns safe error |
| Session timeout | 60 minutes inactivity, session marked COMPLETE |
