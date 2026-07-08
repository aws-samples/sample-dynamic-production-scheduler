# Tech Stack Decisions — Unit 6: Constraint Matching Agent

## Runtime

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Language | Python 3.11+ | Strands Agents SDK requirement, consistent with Units 1, 3, 4, and 5 |
| Agent Framework | Strands Agents SDK | AWS-native agent framework with Bedrock integration |
| Hosting | Bedrock AgentCore managed runtime | Agent registered and hosted via AgentCore — handles scaling and lifecycle |
| Package Manager | pip + pyproject.toml | Consistent with existing units |

## LLM Configuration

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Model | Claude 4.5 Haiku (Bedrock) | Fast inference for interactive per-order reasoning, cost-effective |
| Temperature | 0 | Deterministic tool orchestration and funnel evaluation |
| Max Tokens | 4096 | Sufficient for per-order funnel results + explanation |
| Model ID | Environment variable (BEDROCK_MODEL_ID) | Configurable per environment |

## MCP Tool Access

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Protocol | HTTP/SSE | MCP servers hosted on AgentCore Gateway, accessed via HTTP |
| MCP Framework | FastMCP (server-side) | MCP servers built with FastMCP, hosted on AgentCore Gateway |
| Gateway | AgentCore Gateway | Centralized MCP tool routing and authorization |
| Gateway URL | Environment variable (MCP_GATEWAY_URL) | Configurable per environment |

## Agent Configuration

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Utilization Warning | Configurable via UTILIZATION_WARNING_PCT (default 0.90) | 90% threshold alert |
| Max Cascade Depth | Configurable via MAX_CASCADE_DEPTH (default 5) | Multi-level simulation limit |
| Cascade Timeout | Configurable via CASCADE_TIMEOUT_SECS (default 3) | Layer 4 timeout |
| Checkpoint Interval | Configurable via CHECKPOINT_INTERVAL_SECS (default 300) | Periodic tracker persistence |
| System Prompt | Embedded in agent code | Defines agent persona and tool usage instructions |

## Validation

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Input Validation | Pydantic v2 | Consistent with Units 1, 3, 4, and 5, schema enforcement |
| MCP Response Validation | Pydantic models | Validate tool responses before processing |

## Logging

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Library | Python `logging` | Built-in, consistent with all prior units |
| Format | JSON (structured) | CloudWatch parsing, consistent pattern |
| Level | INFO | Funnel evaluations + decisions + errors |
| Output | stdout | Captured by AgentCore runtime |

## Dependencies

```
# requirements.txt
strands-agents>=0.1.0
strands-agents-tools>=0.1.0
pydantic>=2.0.0
python-json-logger>=2.0.0
```

| Dependency | Purpose |
|------------|---------|
| strands-agents | Strands Agents SDK — agent framework |
| strands-agents-tools | MCP tool integration for Strands agents |
| pydantic | Input/output validation and schema enforcement |
| python-json-logger | JSON log formatting |

Note: boto3 is NOT a direct dependency — Bedrock access is handled by Strands SDK. MCP tool access is via HTTP/SSE to AgentCore Gateway (no local MCP client needed).

## Project Structure

```
constraint-matching-agent/
  src/
    constraint_matching_agent/
      __init__.py
      agent.py             # Agent definition (system prompt, tools, model config)
      funnel.py            # 4-layer constraint funnel (pure Python, no LLM)
      tracker.py           # Running capacity tracker management
      config.py            # AgentConfig (warning pct, cascade depth, timeout), env config
      models/
        __init__.py
        schemas.py         # Pydantic models (FunnelResult, RunningCapacityTracker, etc.)
      prompts/
        __init__.py
        system_prompt.py   # System prompt template
      logging_config.py    # JSON logging setup
  tests/
    __init__.py
    test_funnel.py         # Unit tests for 4-layer constraint funnel
    test_tracker.py        # Unit tests for running capacity tracker
    test_config.py         # Config validation tests
    test_schemas.py        # Schema validation tests
  pyproject.toml
  README.md
```

## Environment Variables

```
BEDROCK_MODEL_ID=us.anthropic.claude-4-5-haiku-20250514-v1:0
MCP_GATEWAY_URL=https://agentcore-gateway.us-east-1.amazonaws.com
UTILIZATION_WARNING_PCT=0.90
MAX_CASCADE_DEPTH=5
CASCADE_TIMEOUT_SECS=3
CHECKPOINT_INTERVAL_SECS=300
LOG_LEVEL=INFO
```
