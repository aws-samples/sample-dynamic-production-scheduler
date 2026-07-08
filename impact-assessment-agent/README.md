# Impact Assessment Agent

> **⚠️ Note:** This is a demo/sample component, not intended for production use without security review.

Priority classification agent for DisruptionAI. Scores and classifies
Florida production orders affected by weather disruptions using a
deterministic scoring algorithm orchestrated by a Strands AI agent.

## Architecture

```
+-----------------------------------------------------------+
|              Bedrock AgentCore Managed Runtime             |
|  +-----------------------------------------------------+  |
|  |          Impact Assessment Agent (Strands)           |  |
|  |                                                      |  |
|  |  +----------------+    +-------------------------+   |  |
|  |  | Python Tools   |    | MCP Tools (via Gateway) |   |  |
|  |  | - score_orders |    | - get_orders            |   |  |
|  |  | - reclassify   |    | - get_customers         |   |  |
|  |  | - summary      |    | - get_capacity          |   |  |
|  |  | - explain      |    | - log_audit_event       |   |  |
|  |  | - group_tables |    | - query_audit_log       |   |  |
|  |  +----------------+    +-------------------------+   |  |
|  +-----------------------------------------------------+  |
+-----------------------------------------------------------+
         |                           |
         v                           v
+----------------+         +-------------------+
| Claude 4.5     |         | AgentCore Gateway |
| Haiku (Bedrock)|         | (SigV4 auth)      |
+----------------+         +-------------------+
                                     |
                           +---------+---------+
                           |                   |
                           v                   v
                   +-------------+     +--------------+
                   | ERP Data    |     | Audit MCP    |
                   | MCP Server  |     | Server       |
                   +-------------+     +--------------+
```

## Project Structure

```
impact-assessment-agent/
  src/impact_assessment_agent/
    __init__.py
    agent.py            # Agent factory, Python tools, fail-closed wrapper
    config.py           # AgentSettings (env-based, Pydantic)
    logging_config.py   # Structured JSON logging
    scoring.py          # Deterministic scoring engine
    models/
      __init__.py
      schemas.py        # Pydantic models (Order, ScoredOrder, etc.)
    prompts/
      system_prompt.py  # LLM system prompt
  tests/
    test_agent.py       # 14 tests
    test_config.py      # 10 tests
    test_schemas.py     # 15 tests
    test_scoring.py     # 18 tests
  pyproject.toml
  requirements.txt
  requirements-dev.txt
```

## Setup

### Prerequisites

- Python 3.11+
- AWS credentials configured (for Bedrock and AgentCore Gateway)

### Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run Tests

```bash
pytest tests/ -v
```

## Configuration

All settings are loaded from environment variables via Pydantic Settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-4-5-haiku-20250514-v1:0` | Bedrock model identifier |
| `MCP_GATEWAY_URL` | `https://agentcore-gateway.us-east-1.amazonaws.com` | AgentCore Gateway endpoint |
| `WEIGHT_URGENCY` | `0.40` | Scoring weight for order urgency |
| `WEIGHT_CUSTOMER_TIER` | `0.25` | Scoring weight for customer tier |
| `WEIGHT_ORDER_VALUE` | `0.20` | Scoring weight for order value |
| `WEIGHT_MACHINE_COMPLEXITY` | `0.15` | Scoring weight for machine complexity |
| `P1_THRESHOLD` | `75` | Minimum score for P1 classification |
| `P2_THRESHOLD` | `50` | Minimum score for P2 classification |
| `LOG_LEVEL` | `INFO` | Logging level |

Weights must sum to 1.0. P1 threshold must be greater than P2 threshold.
Invalid configuration causes a startup failure (fail-fast, Pattern 5).

## Usage

```python
from impact_assessment_agent.agent import create_agent, run_agent

agent = create_agent()
result = run_agent(
    agent,
    task="Score all open Florida orders and show priority summary",
    session_id="session-001",
)

if result.success:
    print(result.data)
else:
    print(f"Error: {result.error}")
```

## Scoring Algorithm

Orders are scored 0-100 using weighted factors:

- Urgency (40%): days until due date
- Customer tier (25%): Platinum > Gold > Silver > Bronze
- Order value (20%): normalized against max value in batch
- Machine complexity (15%): High > Medium > Low

Thresholds determine priority: P1 (>= 75), P2 (>= 50), P3 (< 50).
Planners can override any order's priority; non-pinned orders are
re-evaluated after each override.

## Security

- SigV4 authentication for all MCP Gateway calls
- Fail-closed error handling (Pattern 7) — errors return safe result
- Structured logging with no PII/secrets in output
- Input validation via Pydantic on all data boundaries
- Least-privilege IAM role scoped to specific Bedrock model and Gateway

## License

Internal use only — DisruptionAI project.
