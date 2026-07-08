# NFR Design Patterns — Unit 5: Capacity & Optimization Agent

## Pattern 1: Resilience — LLM Retry with Exponential Backoff

**Applies to**: All Bedrock InvokeModel calls (REL-CO-03)

**Implementation**:
- Strands SDK handles Bedrock retries internally
- Configure retry behavior via SDK agent config
- Retryable: ThrottlingException (backoff 1s, 2s, 4s — 3 attempts max)
- Non-retryable: ModelErrorException, ValidationException
- Timeout: 30 seconds per LLM call (higher than Unit 4 due to more complex orchestration)

```python
from strands import Agent
from strands.models.bedrock import BedrockModel

model = BedrockModel(
    model_id=settings.bedrock_model_id,
    max_tokens=4096,
    temperature=0,  # Deterministic calculations (REL-CO-04)
    timeout=30
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=mcp_tools + python_tools,
    max_retries=3
)
```

---

## Pattern 2: Resilience — MCP Tool Failure Handling (Tiered)

**Applies to**: All MCP tool calls via HTTP/SSE (REL-CO-01)

**Implementation**:
- Agent system prompt instructs LLM on failure behavior per BR-CO-15
- Core tools (get_machine_capacity, get_orders): failure halts agent
- Non-core tools (get_manpower, get_materials): proceed with dimension marked "unavailable"
- Enrichment tools (get_customers): proceed with defaults (penalty_clause=false)
- Audit tools (write_audit_entry): log warning, continue

```python
FAILURE_HANDLING_PROMPT = """
Tool Failure Rules:
- If get_machine_capacity returns an error: STOP immediately. Report the error.
  Machine capacity is required for all calculations.
- If get_orders returns an error: STOP immediately. Report the error.
  Order load is required for surplus and delay calculations.
- If get_manpower returns an error: Continue analysis. Mark manpower dimension
  as "unavailable" in the capacity snapshot. Include warning in summary.
- If get_materials returns an error: Continue analysis. Mark materials dimension
  as "unavailable" in the capacity snapshot. Include warning in summary.
- If get_customers returns an error: Continue analysis. Assume penalty_clause=false
  for all orders. Include warning in summary.
- If write_audit_entry returns an error: Log warning, continue workflow.
"""
```

---

## Pattern 3: Performance — Capacity Calculations as Pure Python

**Applies to**: Surplus, bottleneck, delay filtering, constraint application (PERF-CO-01, PERF-CO-04, PERF-CO-05)

**Implementation**:
- All arithmetic (surplus, utilization, bottleneck ratio, freed capacity, slack) is pure Python
- LLM orchestrates tool calls and generates explanations; calculations are deterministic code
- This keeps the 25s LLM budget for orchestration and natural language generation
- Surplus calculation for 50 orders takes < 5ms (negligible vs LLM and MCP latency)

```python
def compute_tiered_utilization(
    machine_capacity: EquipmentCapability,
    committed_hours: float,
    window_days: int
) -> ShiftUtilization:
    """Deterministic tiered utilization -- no LLM involved."""
    net_hours = machine_capacity.net_available_hours_per_week * (window_days / 5)

    normal_total = net_hours
    normal_committed = min(committed_hours, normal_total)
    normal_surplus = normal_total - normal_committed

    ot_total = machine_capacity.availability_pct_overtime * net_hours
    weekend_total = machine_capacity.availability_pct_weekend * net_hours

    return ShiftUtilization(
        normal=ShiftTier(total=normal_total, committed=normal_committed,
                         surplus=normal_surplus),
        overtime=ShiftTier(total=ot_total, committed=0, surplus=ot_total),
        weekend=ShiftTier(total=weekend_total, committed=0,
                          surplus=weekend_total),
    )


def identify_bottleneck(
    machine_surpluses: dict[str, float],
    florida_demand: dict[str, float]
) -> BottleneckInfo:
    """Ratio-based bottleneck identification (BR-CO-04)."""
    ratios = {}
    for machine, surplus in machine_surpluses.items():
        demand = florida_demand.get(machine, 0)
        ratios[machine] = surplus / demand if demand > 0 else float("inf")

    bottleneck_machine = min(ratios, key=ratios.get)
    return BottleneckInfo(
        machine_type=bottleneck_machine,
        surplus_to_demand_ratio=ratios[bottleneck_machine],
        all_ratios=ratios,
    )
```

The agent exposes `compute_capacity_snapshot`, `filter_delay_candidates`, `apply_constraint`, and `process_delay_decision` as Python tools that the LLM calls after fetching data via MCP tools.

---

## Pattern 4: Observability — Structured Agent Logging

**Applies to**: All agent operations (OBS-CO-01, OBS-CO-02, SECURITY-03)

**Implementation**:
- JSON-formatted logging to stdout (captured by AgentCore runtime)
- Log every MCP tool call: tool name, duration, success/failure
- Log capacity analysis results: surplus summary, bottleneck, utilization
- Log delay decisions: order_id, action, freed capacity
- Log constraint events: constraint_text, before/after delta
- Correlation via session_id

```python
import logging
from pythonjsonlogger import jsonlogger

def configure_agent_logging():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"}
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger("capacity_optimization_agent")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

---

## Pattern 5: Security — Environment-Based Agent Configuration

**Applies to**: All configurable parameters (SEC-CO-02, SECURITY-12)

**Implementation**:
- Bedrock model ID, MCP Gateway URL, business thresholds from environment
- No hardcoded credentials or resource identifiers
- Pydantic Settings for validation at startup

```python
from pydantic_settings import BaseSettings

class AgentSettings(BaseSettings):
    bedrock_model_id: str = "us.anthropic.claude-4-5-haiku-20250514-v1:0"
    mcp_gateway_url: str
    rerouting_window_days: int = 10
    delay_threshold_days: int = 42
    utilization_warning_pct: float = 0.90
    log_level: str = "INFO"

    class Config:
        env_prefix = ""
```

---

## Pattern 6: Security — Input Validation on Agent Entry Points

**Applies to**: Constraint and delay inputs from Orchestrator (SEC-CO-01, SECURITY-05)

**Implementation**:
- Pydantic models validate all inputs before processing
- order_id format validated (PO-YYYY-NNN regex)
- Constraint text length-limited (max 500 chars)
- MCP tool responses validated via Pydantic before calculations

```python
from pydantic import BaseModel, Field

class DelayDecisionInput(BaseModel):
    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    action: str = Field(..., pattern="^(approve|reject)$")
    reason: str = Field(default="", max_length=500)

class ConstraintInput(BaseModel):
    constraint_text: str = Field(..., max_length=500)
    constraint_type: str = Field(
        ..., pattern="^(shift_restriction|capacity_limit|other)$"
    )
```

---

## Pattern 7: Resilience — Fail-Closed Agent Wrapper

**Applies to**: Agent entry point (SEC-CO-05, SECURITY-15)

**Implementation**:
- Global exception handler wraps agent invocation
- On unhandled exception: return error to Orchestrator, do not proceed
- Capacity analysis is all-or-nothing (no partial snapshots)
- Delay decisions already persisted are NOT rolled back on subsequent failure

```python
async def run_agent(task: str, session_id: str) -> AgentResult:
    try:
        logger.info("Agent invoked", extra={
            "agent": "capacity_optimization_agent",
            "session_id": session_id
        })
        result = await agent(task)
        return AgentResult(success=True, data=result)
    except Exception as e:
        logger.error("Agent failed", extra={
            "agent": "capacity_optimization_agent",
            "session_id": session_id,
            "error": str(e)
        }, exc_info=True)
        return AgentResult(
            success=False,
            error="Capacity Optimization Agent encountered an error"
        )
```

---

## Pattern 8: Performance — Cached Snapshot for Recalculations

**Applies to**: Delay decisions and constraint recalculations (PERF-CO-04, PERF-CO-05)

**Implementation**:
- After initial capacity analysis, the CapacitySnapshot is cached in-memory
- Delay decisions and constraint applications operate on the cached snapshot
- No MCP data re-fetch needed for recalculations (pure arithmetic on cached data)
- Updated snapshot is persisted to AgentCore Memory after each mutation
- This keeps delay/constraint response times within 10s budget

```python
class CapacityState:
    """In-memory cache of current capacity snapshot for fast recalculations."""

    def __init__(self, snapshot: CapacitySnapshot):
        self._snapshot = snapshot

    def apply_delay(self, order_id: str, freed: FreedCapacity) -> CapacitySnapshot:
        """Add freed capacity, recalculate bottleneck. O(1) per decision."""
        self._snapshot.surplus.rolling_mill += freed.rolling_mill_hours
        self._snapshot.surplus.finishing_line += freed.finishing_line_hours
        self._snapshot.delays_approved.append(order_id)
        self._snapshot.bottleneck = identify_bottleneck(...)
        return self._snapshot

    def apply_constraint(self, constraint: PlannerConstraint) -> CapacitySnapshot:
        """Apply constraint, recalculate all surplus values."""
        # ... constraint application logic
        self._snapshot.bottleneck = identify_bottleneck(...)
        return self._snapshot
```
