# Capacity & Optimization Agent

> **⚠️ Note:** This is a demo/sample component, not intended for production use without security review.

Strands Agents SDK agent for DisruptionAI that performs 5-dimension capacity analysis of the Ohio steel plant, identifies delay candidates among low-priority orders, and supports planner-driven constraint application — all to determine whether Florida rerouted orders can be absorbed.

## Architecture

- **Runtime**: AWS Bedrock AgentCore managed runtime
- **LLM**: Claude 4.5 Haiku (`us.anthropic.claude-4-5-haiku-20250514-v1:0`)
- **Framework**: Strands Agents SDK with `@tool` decorated Python functions
- **MCP Integration**: ERP Data MCP + Audit MCP via `mcp-proxy-for-aws` (SigV4 auth to AgentCore Gateway)
- **Pattern 8 — Cached Snapshot**: After initial MCP data fetch, all delay decisions and constraint applications operate on in-memory cached state for fast recalculations without MCP re-fetch

## Package Structure

```
capacity-optimization-agent/
  src/capacity_optimization_agent/
    __init__.py
    config.py              # AgentSettings (env-driven, Pydantic)
    logging_config.py      # JSON structured logging to stdout
    capacity.py            # Core engine: utilization, bottleneck, delay filtering, CapacityState
    agent.py               # 5 Python tools, MCP client factory, create_agent(), run_agent()
    models/
      __init__.py
      schemas.py           # 20 Pydantic models (CapacitySnapshot, OhioOrderLoad, etc.)
    prompts/
      __init__.py
      system_prompt.py     # System prompt with workflow constants
  tests/
    __init__.py
    test_schemas.py        # 43 tests
    test_config.py         # 6 tests
    test_capacity.py       # 29 tests
    test_agent.py          # 20 tests
  pyproject.toml
  requirements.txt
```

## Python Tools (exposed to LLM)

| Tool | Purpose |
|---|---|
| `compute_capacity_snapshot` | Full 5-dimension analysis; caches result |
| `filter_delay_candidates_tool` | Identify P3 orders eligible for delay |
| `process_delay_decision` | Apply approve/reject on cached state |
| `apply_constraint_tool` | Apply shift/capacity constraints |
| `check_utilization_warnings_tool` | Flag machines above threshold |

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Tests

```bash
pytest tests/ -v
# 98 tests, ~0.6s
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MCP_GATEWAY_URL` | Yes | — | AgentCore Gateway endpoint |
| `BEDROCK_MODEL_ID` | No | `us.anthropic.claude-4-5-haiku-20250514-v1:0` | LLM model |
| `REROUTING_WINDOW_DAYS` | No | `10` | Analysis window |
| `DELAY_THRESHOLD_DAYS` | No | `42` | Min slack for delay eligibility |
| `UTILIZATION_WARNING_PCT` | No | `0.90` | Warning threshold |
| `LOG_LEVEL` | No | `INFO` | Logging level |
