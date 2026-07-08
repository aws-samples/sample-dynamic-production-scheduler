# Rework Cycle 3 — Backend Code Generation Summary

## Requirements Implemented
- REQ-B01: Sub-agent max_tokens 4096 → 8192 (impact, capacity, constraint agents)
- REQ-B02: Per-invocation agent instances — `_create_agent_per_request()` factory in orchestrator
- REQ-B03: Data staging tool pattern — `stage_erp_data` tool added to all 3 sub-agents; scoring/funnel tools refactored to read from `_staged_data` with fallback to direct params
- REQ-B04: Plant-agnostic naming — `ohio_orders_json` → `receiving_plant_orders_json`; all 3 system prompts updated to generic "disrupted plant"/"receiving plant"
- REQ-B05: 30-second retry delay — `retry_delay_seconds` config + `time.sleep()` before retry
- REQ-B06: Orchestrator max_tokens 8192 → 16384

## Files Modified
| File | Change |
|------|--------|
| `impact-assessment-agent/src/impact_assessment_agent/agent.py` | max_tokens=8192, stage_erp_data tool, _staged_data reset in create_agent |
| `impact-assessment-agent/src/impact_assessment_agent/prompts/system_prompt.py` | Plant-agnostic references |
| `capacity-optimization-agent/src/capacity_optimization_agent/agent.py` | max_tokens=8192, stage_erp_data tool, compute_capacity_snapshot reads staged data |
| `capacity-optimization-agent/src/capacity_optimization_agent/prompts/system_prompt.py` | Plant-agnostic references |
| `constraint-matching-agent/src/constraint_matching_agent/agent.py` | max_tokens=8192, stage_erp_data tool, receiving_plant_orders_json rename |
| `constraint-matching-agent/src/constraint_matching_agent/prompts/system_prompt.py` | Plant-agnostic references |
| `orchestrator-agent/src/orchestrator_agent/agent.py` | max_tokens=16384, retry delay |
| `orchestrator-agent/src/orchestrator_agent/config.py` | retry_delay_seconds=30 |
| `orchestrator-agent/src/orchestrator_agent/agentcore_server.py` | Per-request agent factory |
