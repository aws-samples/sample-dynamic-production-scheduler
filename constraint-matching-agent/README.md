# Constraint Matching Agent

> **⚠️ Note:** This is a demo/sample component, not intended for production use without security review.

Strands-based AI agent that evaluates Florida production orders against Ohio plant constraints using a 4-layer funnel engine. Runs on Bedrock AgentCore managed runtime with Claude 4.5 Haiku.

## Architecture

The agent processes prioritized Florida orders (from Impact Assessment Agent) through:

1. **Layer 1 — Equipment Compatibility**: Machine type support, gauge range, product family
2. **Layer 2 — Material Availability**: Surplus inventory, procurement feasibility vs due date
3. **Layer 3 — Utilization & Workforce**: Shift-tiered hours (normal/overtime/weekend), operator counts
4. **Layer 4 — Cascade Impact**: Multi-level Ohio schedule displacement simulation

Each order receives a composite recommendation: Transfer, Transfer with procurement, Transfer on overtime/weekend, Transfer with conditions, or Non-transferable.

## Key Components

- `models/schemas.py` — Pydantic models for funnel results, tracker state, audit entries
- `config.py` — Environment-based configuration with Pydantic validation
- `funnel.py` — Deterministic 4-layer constraint engine
- `tracker.py` — Running capacity singleton with tiered hour consumption
- `prompts/system_prompt.py` — LLM system prompt with workflow and decision rules
- `agent.py` — Strands Agent factory, Python tool wrappers, fail-closed runner

## MCP Dependencies

Accessed via AgentCore Gateway (HTTP/SSE with SigV4):

- **ERP Data MCP** — Orders, customers, equipment, materials, workforce, capacity
- **Audit MCP** — Decision logging and audit trail

## Setup

```bash
pip install -e .
```

## Configuration

Environment variables (all have defaults):

| Variable | Default | Description |
|---|---|---|
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-4-5-haiku-20250514-v1:0` | LLM model |
| `MCP_GATEWAY_URL` | `https://agentcore-gateway.us-east-1.amazonaws.com` | AgentCore Gateway |
| `UTILIZATION_WARNING_PCT` | `0.90` | Utilization warning threshold |
| `MAX_CASCADE_DEPTH` | `5` | Max cascade simulation levels |
| `CASCADE_TIMEOUT_SECS` | `3` | Cascade simulation timeout |
| `LOG_LEVEL` | `INFO` | Logging level |

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Usage

```python
from constraint_matching_agent.agent import create_agent, run_agent

agent = create_agent()
result = run_agent(agent, "Evaluate Florida orders for transfer", "session-123")
```
