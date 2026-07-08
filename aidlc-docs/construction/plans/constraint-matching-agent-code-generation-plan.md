# Code Generation Plan — Unit 6: Constraint Matching Agent

## Context
- **Unit**: Unit 6 — Constraint Matching Agent
- **Language**: Python 3.11+
- **Framework**: Strands Agents SDK
- **Hosting**: Bedrock AgentCore managed runtime
- **LLM**: Claude 4.5 Haiku (Bedrock)
- **MCP Access**: HTTP/SSE via AgentCore Gateway (ERP Data MCP + Audit MCP)
- **Code Location**: `constraint-matching-agent/` (workspace root)

## Stories Implemented
- US-07: 4-layer constraint funnel evaluation per Florida order
- US-08: Running capacity tracker with tiered hour consumption
- US-09: Per-order presentation with approve/reject/skip decisions
- US-10: Cascade impact simulation for Ohio schedule

## Execution Steps

- [x] Step 1: Project structure setup (pyproject.toml, requirements.txt, __init__.py files)
- [x] Step 2: Pydantic schema models (models/schemas.py)
- [x] Step 3: Schema unit tests (tests/test_schemas.py)
- [x] Step 4: Agent configuration (config.py)
- [x] Step 5: Configuration unit tests (tests/test_config.py)
- [x] Step 6: Logging configuration (logging_config.py)
- [x] Step 7: Funnel engine (funnel.py) — 4-layer constraint funnel + cascade simulation
- [x] Step 8: Funnel engine unit tests (tests/test_funnel.py)
- [x] Step 9: Tracker module (tracker.py) — TrackerState singleton with tiered consumption
- [x] Step 10: Tracker unit tests (tests/test_tracker.py)
- [x] Step 11: System prompt (prompts/system_prompt.py)
- [x] Step 12: Agent entry point (agent.py) — Python tools, MCP client, create_agent(), run_agent()
- [x] Step 13: Agent unit tests (tests/test_agent.py)
- [x] Step 14: README.md
- [x] Step 15: Code generation summary (aidlc-docs)
