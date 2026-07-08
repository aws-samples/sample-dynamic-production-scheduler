# Tech Stack Decisions — Unit 5: Capacity & Optimization Agent

## Runtime

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Language | Python 3.11+ | Strands Agents SDK requirement, consistent with Units 1, 3, and 4 |
| Agent Framework | Strands Agents SDK | AWS-native agent framework with Bedrock integration |
| Hosting | Bedrock AgentCore managed runtime | Agent registered and hosted via AgentCore — handles scaling and lifecycle |
| Package Manager | pip + requirements.txt | Consistent with existing units |

## LLM Configuration

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Model | Claude 4.5 Haiku (Bedrock) | Fast inference for structured analysis tasks, cost-effective |
| Temperature | 0 | Deterministic tool orchestration and calculations |
| Max Tokens | 4096 | Sufficient for surplus tables + delay candidate lists + explanations |
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
| Rerouting Window | Configurable via REROUTING_WINDOW_DAYS (default 10) | Business-configurable analysis scope |
| Delay Threshold | Configurable via DELAY_THRESHOLD_DAYS (default 42) | Business-configurable eligibility cutoff |
| Utilization Warning | Configurable via UTILIZATION_WARNING_PCT (default 0.90) | Alerting threshold for overtime escalation |
| System Prompt | Embedded in agent code | Defines agent persona and tool usage instructions |

## Validation

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Input Validation | Pydantic v2 | Consistent with Units 1, 3, and 4, schema enforcement |
| MCP Response Validation | Pydantic models | Validate tool responses before processing |

## Logging

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Library | Python `logging` | Built-in, consistent with Units 1, 3, and 4 |
| Format | JSON (structured) | CloudWatch parsing, consistent pattern |
| Level | INFO | Tool calls + analysis results + decisions + errors |
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
capacity-optimization-agent/
  src/
    capacity_optimization_agent/
      __init__.py
      agent.py             # Agent definition (system prompt, tools, model config)
      capacity.py          # Surplus calculation, bottleneck ID, delay filtering (pure Python)
      config.py            # AgentConfig (window, threshold, utilization), env config
      models/
        __init__.py
        schemas.py         # Pydantic models (CapacitySnapshot, BottleneckInfo, DelayCandidate, etc.)
      prompts/
        __init__.py
        system_prompt.py   # System prompt template
      logging_config.py    # JSON logging setup
  tests/
    __init__.py
    test_capacity.py       # Unit tests for surplus/bottleneck/delay calculations
    test_config.py         # Config validation tests
    test_schemas.py        # Schema validation tests
  requirements.txt
  README.md
```

## Environment Variables

```
BEDROCK_MODEL_ID=us.anthropic.claude-4-5-haiku-20250514-v1:0
MCP_GATEWAY_URL=https://agentcore-gateway.us-east-1.amazonaws.com
REROUTING_WINDOW_DAYS=10
DELAY_THRESHOLD_DAYS=42
UTILIZATION_WARNING_PCT=0.90
LOG_LEVEL=INFO
```
