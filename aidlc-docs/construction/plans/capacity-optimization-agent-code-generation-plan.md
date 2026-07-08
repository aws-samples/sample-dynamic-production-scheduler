# Code Generation Plan — Unit 5: Capacity & Optimization Agent

## Context
- **Unit**: Unit 5 — Capacity & Optimization Agent
- **Language**: Python 3.11+
- **Framework**: Strands Agents SDK
- **Hosting**: Bedrock AgentCore managed runtime
- **LLM**: Claude 4.5 Haiku (Bedrock)
- **MCP Access**: HTTP/SSE via AgentCore Gateway (ERP Data MCP + Audit MCP)
- **Code Location**: `capacity-optimization-agent/` (workspace root)

## Stories Implemented
- US-04: Ohio capacity analysis across 5 dimensions (equipment, utilization, manpower, materials, existing load)
- US-05: Planner constraint handling with immediate recalculation
- US-06: Delay optimization (candidate identification, approval/rejection, freed capacity recalculation)

## Execution Steps

- [x] Step 1: Project structure setup (requirements.txt, __init__.py files)
- [x] Step 2: Pydantic schema models (models/schemas.py)
- [x] Step 3: Schema unit tests (tests/test_schemas.py)
- [x] Step 4: Agent configuration (config.py)
- [x] Step 5: Configuration unit tests (tests/test_config.py)
- [x] Step 6: Logging configuration (logging_config.py)
- [x] Step 7: Capacity engine (capacity.py) — surplus, bottleneck, delay, constraint calculations
- [x] Step 8: Capacity engine unit tests (tests/test_capacity.py)
- [x] Step 9: System prompt (prompts/system_prompt.py)
- [x] Step 10: Agent entry point (agent.py)
- [x] Step 11: Agent unit tests (tests/test_agent.py)
- [x] Step 12: README.md
- [x] Step 13: Code generation summary (aidlc-docs)
