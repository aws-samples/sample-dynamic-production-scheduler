# Tech Stack Decisions — Unit 4: Impact Assessment Agent

## Runtime

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Language | Python 3.11+ | Strands Agents SDK requirement, consistent with Units 1 and 3 |
| Agent Framework | Strands Agents SDK | AWS-native agent framework with Bedrock integration |
| Hosting | Bedrock AgentCore managed runtime | Agent registered and hosted via AgentCore — handles scaling and lifecycle |
| Package Manager | pip + requirements.txt | Consistent with existing units |

## LLM Configuration

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Model | Claude 4.5 Haiku (Bedrock) | Fast inference for structured scoring tasks, cost-effective |
| Temperature | 0 | Deterministic tool orchestration and scoring |
| Max Tokens | 4096 | Sufficient for summary + table generation |
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
| Scoring Weights | Python dataclass + env override | Default urgency-heavy, runtime configurable |
| Priority Thresholds | Python dataclass + env override | Default 75/50, runtime configurable |
| System Prompt | Embedded in agent code | Defines agent persona and tool usage instructions |

## Validation

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Input Validation | Pydantic v2 | Consistent with Units 1 and 3, schema enforcement |
| MCP Response Validation | Pydantic models | Validate tool responses before processing |

## Logging

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Library | Python `logging` | Built-in, consistent with Units 1 and 3 |
| Format | JSON (structured) | CloudWatch parsing, consistent pattern |
| Level | INFO | Tool calls + classification results + errors |
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
impact-assessment-agent/
  src/
    impact_assessment_agent/
      __init__.py
      agent.py             # Agent definition (system prompt, tools, model config)
      scoring.py           # Priority scoring algorithm (pure Python, no LLM)
      config.py            # ScoringWeights, PriorityThresholds, env config
      models/
        __init__.py
        schemas.py         # Pydantic models (ScoredOrder, PrioritySummary, etc.)
      prompts/
        __init__.py
        system_prompt.py   # System prompt template
      logging_config.py    # JSON logging setup
  tests/
    __init__.py
    test_scoring.py        # Unit tests for scoring algorithm
    test_config.py         # Config validation tests
    test_schemas.py        # Schema validation tests
  requirements.txt
  README.md
```

## Environment Variables

```
BEDROCK_MODEL_ID=us.anthropic.claude-4-5-haiku-20250514-v1:0
MCP_GATEWAY_URL=https://agentcore-gateway.us-east-1.amazonaws.com
WEIGHT_URGENCY=0.40
WEIGHT_CUSTOMER_TIER=0.25
WEIGHT_ORDER_VALUE=0.20
WEIGHT_MACHINE_COMPLEXITY=0.15
P1_THRESHOLD=75
P2_THRESHOLD=50
LOG_LEVEL=INFO
```
