# Orchestrator Agent — DisruptionAI

> **⚠️ Note:** This is a demo/sample component, not intended for production use without security review.

Top-level coordinator for the DisruptionAI dynamic production scheduling workflow. Receives disruption events from the Planner, orchestrates sub-agents (Impact Assessment, Capacity Optimization, Constraint Matching) through a 6-phase workflow, and streams structured results back.

## Architecture

- **Framework**: Strands Agents SDK with Bedrock Claude 4.5 Haiku
- **Hosting**: AWS Bedrock AgentCore managed runtime
- **Sub-agents**: Invoked via AgentCore API (not in-process)
- **MCP Access**: Audit MCP via AgentCore Gateway (SigV4 auth)
- **Session State**: In-process WorkflowSession with AgentCore Memory fallback

## Project Structure

```
orchestrator-agent/
  src/orchestrator_agent/
    __init__.py
    agent.py              # Agent factory, sub-agent tools, run wrapper
    config.py             # OrchestratorSettings (pydantic-settings)
    session.py            # WorkflowSession state machine
    logging_config.py     # JSON structured logging
    models/
      schemas.py          # Pydantic domain models
    prompts/
      system_prompt.py    # 6-phase workflow system prompt
  tests/
    test_schemas.py       # 22 tests
    test_config.py        #  7 tests
    test_session.py       # 16 tests
    test_agent.py         # 15 tests
  pyproject.toml
  README.md
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-4-5-haiku-20250514-v1:0` | LLM model ID |
| `MCP_GATEWAY_URL` | `https://agentcore-gateway.us-east-1.amazonaws.com` | AgentCore Gateway |
| `IMPACT_ASSESSMENT_AGENT_ID` | *(required)* | AgentCore agent ID for Impact Assessment |
| `CAPACITY_OPTIMIZATION_AGENT_ID` | *(required)* | AgentCore agent ID for Capacity Optimization |
| `CONSTRAINT_MATCHING_AGENT_ID` | *(required)* | AgentCore agent ID for Constraint Matching |
| `AUDIT_MCP_URL` | *(required)* | Audit MCP endpoint on AgentCore Gateway |
| `SESSION_TIMEOUT_MINUTES` | `60` | Session expiry |
| `MAX_TURNS` | `100` | Max LLM conversation turns |
| `RETRY_LIMIT` | `1` | Sub-agent invocation retries |
| `LOG_LEVEL` | `INFO` | Logging level |

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Dependencies

- `strands-agents` — Strands Agents SDK
- `strands-agents-tools` — MCP tool integration
- `pydantic` / `pydantic-settings` — Validation and config
- `python-json-logger` — Structured JSON logging
- `mcp-proxy-for-aws` — SigV4 auth for AgentCore Gateway

## Workflow Phases

1. **Disruption Intake** — Parse and validate disruption event
2. **Impact Assessment (Round 1)** — Invoke Impact Assessment Agent
3. **Delay Propagation (Round 2)** — Invoke Capacity Optimization for delays
4. **Constraint Funnel (Round 2)** — Invoke Constraint Matching for feasibility
5. **What-If Exploration** — Optional scenario analysis
6. **Summary & Commit** — Compile decisions, write audit log
