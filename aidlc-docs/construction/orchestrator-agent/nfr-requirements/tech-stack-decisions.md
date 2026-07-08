# Tech Stack Decisions — Unit 7: Orchestrator Agent

## Runtime

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Language | Python 3.11+ | Strands Agents SDK requirement, consistent with Units 1-6 |
| Agent Framework | Strands Agents SDK | AWS-native agent framework with Bedrock integration |
| Hosting | Bedrock AgentCore managed runtime | Agent registered and hosted via AgentCore |
| Package Manager | pip + pyproject.toml | Consistent with existing units |

## LLM Configuration

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Model | Claude 4.5 Haiku (Bedrock) | Fast inference for orchestration and routing |
| Temperature | 0 | Deterministic tool orchestration |
| Max Tokens | 8192 | Larger budget for summaries spanning full workflow |
| Model ID | Environment variable (BEDROCK_MODEL_ID) | Configurable per environment |

## Sub-Agent Invocation

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Pattern | Strands Agent-as-Tool | LLM decides when to invoke sub-agents |
| Transport | AgentCore managed runtime API | Sub-agents are separate AgentCore agents |
| Agent IDs | Environment variables | Configurable per environment |
| Retry | 1 retry on failure | Per BR-OA-08 |

## MCP Tool Access

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Protocol | HTTP/SSE | MCP servers hosted on AgentCore Gateway |
| MCP Client | mcp-proxy-for-aws (SigV4 auth) | Secure access to AgentCore Gateway |
| Direct MCP Access | Audit MCP only | ERP data access delegated to sub-agents |

## Shared Context

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Mechanism | AgentCore Memory | AWS managed, session-scoped |
| Keys | prioritized_orders, capacity_snapshot, workflow_session | Per domain-entities.md |
| Fallback | In-process dict | If AgentCore Memory unavailable |

## Session State

| Component | Decision | Rationale |
|-----------|----------|-----------|
| LLM Context | Strands conversation history | Built-in context window management |
| Programmatic State | WorkflowSession dataclass | Phase tracking, decisions, errors |
| Persistence | AgentCore Memory | Recovery on reconnection |

## Validation

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Input Validation | Pydantic v2 | Schema enforcement on Planner messages |
| Response Validation | Pydantic models | Validate sub-agent responses |

## Logging

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Library | Python `logging` | Built-in, consistent with Units 1-6 |
| Format | JSON (structured) | CloudWatch parsing |
| Level | INFO | Phase transitions + sub-agent calls + decisions |
| Output | stdout | Captured by AgentCore runtime |

## Dependencies

```
# pyproject.toml [project.dependencies]
strands-agents>=0.1.0
strands-agents-tools>=0.1.0
pydantic>=2.0.0
python-json-logger>=2.0.0
mcp-proxy-for-aws>=0.1.0
```

| Dependency | Purpose |
|------------|---------|
| strands-agents | Strands Agents SDK — agent framework |
| strands-agents-tools | MCP tool integration for Strands agents |
| pydantic | Input/output validation and schema enforcement |
| python-json-logger | JSON log formatting |
| mcp-proxy-for-aws | SigV4 auth for AgentCore Gateway MCP access |

## Project Structure

```
orchestrator-agent/
  src/
    orchestrator_agent/
      __init__.py
      agent.py             # Agent definition, sub-agent tools, model config
      config.py            # OrchestratorConfig, env config
      session.py           # WorkflowSession state management
      models/
        __init__.py
        schemas.py         # Pydantic models (all domain entities)
      prompts/
        __init__.py
        system_prompt.py   # System prompt template
      logging_config.py    # JSON logging setup
  tests/
    __init__.py
    test_session.py        # Session state tests
    test_config.py         # Config validation tests
    test_schemas.py        # Schema validation tests
    test_agent.py          # Agent tool and wrapper tests
  pyproject.toml
  README.md
```

## Environment Variables

```
BEDROCK_MODEL_ID=us.anthropic.claude-4-5-haiku-20250514-v1:0
MCP_GATEWAY_URL=https://agentcore-gateway.us-east-1.amazonaws.com
IMPACT_ASSESSMENT_AGENT_ID=<agentcore-agent-id>
CAPACITY_OPTIMIZATION_AGENT_ID=<agentcore-agent-id>
CONSTRAINT_MATCHING_AGENT_ID=<agentcore-agent-id>
AUDIT_MCP_URL=https://agentcore-gateway.us-east-1.amazonaws.com/audit-mcp
SESSION_TIMEOUT_MINUTES=60
MAX_TURNS=100
RETRY_LIMIT=1
LOG_LEVEL=INFO
```
