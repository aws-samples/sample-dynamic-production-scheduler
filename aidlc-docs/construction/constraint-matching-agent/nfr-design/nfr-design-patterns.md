# NFR Design Patterns — Unit 6: Constraint Matching Agent

## Pattern 1: Resilience — LLM Retry with Exponential Backoff

**Applies to**: All Bedrock InvokeModel calls (REL-CM-03)

**Implementation**:
- Strands SDK handles Bedrock retries internally
- Configure retry behavior via SDK agent config
- Retryable: ThrottlingException (backoff 1s, 2s, 4s — 3 attempts max)
- Non-retryable: ModelErrorException, ValidationException
- Timeout: 20 seconds per LLM call

```python
from strands import Agent
from strands.models.bedrock import BedrockModel

model = BedrockModel(
    model_id=settings.bedrock_model_id,
    max_tokens=4096,
    temperature=0,  # Deterministic funnel evaluation (REL-CM-04)
    timeout=20
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

**Applies to**: All MCP tool calls via HTTP/SSE (REL-CM-01)

**Implementation**:
- Agent system prompt instructs LLM on failure behavior per BR-CM-13
- Core tools (get_machine_capacity): failure halts agent — equipment data required for Layer 1
- Non-core tools (get_materials, get_manpower): proceed with degraded layer results
- Ohio schedule (get_orders): Layer 4 defaults to PASS with warning
- Tracker tools (get_running_tracker): initialize fresh from snapshot
- Persistence tools (update_running_tracker): log warning, continue in-memory
- Audit tools (write_audit_entry): log warning, continue

```python
FAILURE_HANDLING_PROMPT = """
Tool Failure Rules:
- If get_machine_capacity returns an error: STOP immediately. Report the error.
  Equipment data is required for Layer 1 compatibility checks.
- If get_materials returns an error: Continue. Layer 2 defaults to "No Match"
  with warning "Material data unavailable".
- If get_orders(plant="Ohio") returns an error: Continue. Layer 4 defaults to
  PASS with warning "Ohio schedule unavailable — cascade not verified".
- If get_manpower returns an error: Continue. Manpower check defaults to soft
  warning "Manpower data unavailable".
- If get_running_tracker returns an error: Initialize fresh tracker from
  shared context snapshot.
- If update_running_tracker returns an error: Log warning, continue with
  in-memory tracker. Note audit gap.
- If write_audit_entry returns an error: Log warning, continue workflow.
"""
```

---

## Pattern 3: Performance — Constraint Funnel as Pure Python (Hybrid Tool Design)

**Applies to**: 4-layer funnel evaluation and cascade simulation (PERF-CM-01, PERF-CM-05)

**Implementation**:
- All 4 funnel layers implemented as pure Python — no LLM calls for constraint checks
- LLM orchestrates tool calls and generates natural language explanations
- Hybrid tool design (per user decision Q1=C):
  - `evaluate_funnel(order)` — runs all 4 layers in one call, returns composite FunnelResult
  - `simulate_cascade(order)` — standalone cascade simulation for on-demand re-runs
- Funnel evaluation for 1 order takes < 10ms (negligible vs LLM and MCP latency)
- Cascade simulation with 20 Ohio orders at depth 5: < 50ms

```python
def evaluate_funnel(
    order: dict,
    equipment: list[dict],
    materials: dict,
    manpower: dict,
    ohio_orders: list[dict],
    tracker: RunningCapacityTracker,
    config: AgentConfig
) -> FunnelResult:
    """Run all 4 constraint layers. Pure Python, deterministic."""
    l1 = check_equipment_compatibility(order, equipment)
    l2 = check_material_availability(order, materials, tracker)
    l3 = check_utilization_and_manpower(order, tracker, manpower, config)
    l4 = simulate_cascade(order, ohio_orders, config)
    recommendation = derive_recommendation(l1, l2, l3, l4)
    return FunnelResult(
        order_id=order["order_id"],
        layer1=l1, layer2=l2, layer3=l3, layer4=l4,
        recommendation=recommendation
    )


def simulate_cascade(
    florida_order: dict,
    ohio_orders: list[dict],
    config: AgentConfig
) -> CascadeImpactResult:
    """Standalone cascade simulation with timeout enforcement."""
    import time
    start = time.monotonic()
    timeout = config.cascade_timeout_secs
    impacted = []
    # ... multi-level cascade logic with timeout check ...
    timed_out = (time.monotonic() - start) > timeout
    return CascadeImpactResult(
        impacted_orders=impacted,
        timed_out=timed_out,
        max_depth_reached=depth
    )
```

The agent registers both `evaluate_funnel` and `simulate_cascade` as Strands Python tools. The LLM calls `evaluate_funnel` for each order in the queue, and can call `simulate_cascade` independently if the Planner requests a re-simulation.

---

## Pattern 4: Observability — Structured Agent Logging

**Applies to**: All agent operations (OBS-CM-01, OBS-CM-02, SECURITY-03)

**Implementation**:
- JSON-formatted logging to stdout (captured by AgentCore runtime)
- Log every MCP tool call: tool name, duration, success/failure
- Log every funnel evaluation: order_id, layer results, recommendation
- Log every planner decision: order_id, action, capacity consumed
- Log cascade simulation: depth reached, orders impacted, timeout status
- Correlation via session_id and order_id

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
    logger = logging.getLogger("constraint_matching_agent")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

---

## Pattern 5: Security — Environment-Based Agent Configuration

**Applies to**: All configurable parameters (SEC-CM-02, SECURITY-12)

**Implementation**:
- Bedrock model ID, MCP Gateway URL, business thresholds from environment
- No hardcoded credentials or resource identifiers
- Pydantic Settings for validation at startup

```python
from pydantic_settings import BaseSettings

class AgentSettings(BaseSettings):
    bedrock_model_id: str = "us.anthropic.claude-4-5-haiku-20250514-v1:0"
    mcp_gateway_url: str
    utilization_warning_pct: float = 0.90
    max_cascade_depth: int = 5
    cascade_timeout_secs: int = 3
    checkpoint_interval_secs: int = 300
    log_level: str = "INFO"

    class Config:
        env_prefix = ""
```

---

## Pattern 6: Security — Input Validation on Agent Entry Points

**Applies to**: All inputs from Orchestrator and Planner decisions (SEC-CM-01, SECURITY-05)

**Implementation**:
- Pydantic models validate all inputs before processing
- order_id format validated (PO-YYYY-NNN regex)
- Decision action validated (approve/reject/skip enum)
- MCP tool responses validated via Pydantic before funnel evaluation
- Revisit order_id validated against known order set

```python
from pydantic import BaseModel, Field

class OrderDecisionInput(BaseModel):
    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    action: str = Field(..., pattern="^(approve|reject|skip)$")
    reason: str = Field(default="", max_length=500)

class RevisitInput(BaseModel):
    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
```

---

## Pattern 7: Resilience — Fail-Closed Agent Wrapper

**Applies to**: Agent entry point (SEC-CM-05, SECURITY-15)

**Implementation**:
- Global exception handler wraps agent invocation
- On unhandled exception: return error to Orchestrator, do not proceed
- Tracker state already persisted is NOT rolled back on subsequent failure
- Cascade simulation timeout returns partial results (graceful degradation, not failure)

```python
async def run_agent(task: str, session_id: str) -> AgentResult:
    try:
        logger.info("Agent invoked", extra={
            "agent": "constraint_matching_agent",
            "session_id": session_id
        })
        result = await agent(task)
        return AgentResult(success=True, data=result)
    except Exception as e:
        logger.error("Agent failed", extra={
            "agent": "constraint_matching_agent",
            "session_id": session_id,
            "error": str(e)
        }, exc_info=True)
        return AgentResult(
            success=False,
            error="Constraint Matching Agent encountered an error"
        )
```

---

## Pattern 8: Performance — Running Capacity Tracker (Module-Level Singleton)

**Applies to**: Tracker state management across funnel evaluations and decisions (PERF-CM-06, REL-CM-02)

**Implementation**:
- Module-level singleton tracker (per user decision Q2=A), consistent with Unit 5's CapacityState
- Initialized from shared context snapshot or loaded from DynamoDB on session resumption
- All funnel functions and decision handlers access the singleton directly
- Tracker persisted to DynamoDB via `update_running_tracker` after every planner decision
- Periodic checkpoint every 5 minutes during idle periods
- Session-scoped via session_id — no cross-session interference

```python
class TrackerState:
    """Module-level singleton for running capacity tracker."""

    _instance: "TrackerState | None" = None

    def __init__(self, tracker: RunningCapacityTracker):
        self._tracker = tracker

    @classmethod
    def initialize(cls, tracker: RunningCapacityTracker) -> "TrackerState":
        cls._instance = cls(tracker)
        return cls._instance

    @classmethod
    def get(cls) -> "TrackerState":
        if cls._instance is None:
            raise RuntimeError("TrackerState not initialized")
        return cls._instance

    @property
    def tracker(self) -> RunningCapacityTracker:
        return self._tracker

    def consume_hours(self, machine: str, required_hrs: float) -> float:
        """Tiered consumption: normal -> overtime -> weekend."""
        hrs = getattr(self._tracker, f"{machine}_remaining_hrs")
        remaining = required_hrs

        normal_consumed = min(hrs.normal_hrs, remaining)
        hrs.normal_hrs -= normal_consumed
        remaining -= normal_consumed

        if remaining > 0:
            ot_consumed = min(hrs.overtime_hrs, remaining)
            hrs.overtime_hrs -= ot_consumed
            remaining -= ot_consumed

        if remaining > 0:
            wk_consumed = min(hrs.weekend_hrs, remaining)
            hrs.weekend_hrs -= wk_consumed
            remaining -= wk_consumed

        hrs.total_hrs = hrs.normal_hrs + hrs.overtime_hrs + hrs.weekend_hrs
        return remaining  # should be 0 if Layer 3 passed

    def approve_order(self, order_id: str, rm_hrs: float,
                      fl_hrs: float, material_tons: float,
                      manpower: float) -> None:
        """Deduct all capacity dimensions for an approved order."""
        self.consume_hours("rolling_mill", rm_hrs)
        self.consume_hours("finishing_line", fl_hrs)
        self._tracker.material_remaining_tons -= material_tons
        self._tracker.manpower_remaining -= manpower
        self._tracker.orders_approved.append(order_id)

    def skip_order(self, order_id: str) -> None:
        self._tracker.orders_skipped.append(order_id)

    def reject_order(self, order_id: str) -> None:
        self._tracker.orders_rejected.append(order_id)
```

---

## Pattern 9: Resilience — Cascade Simulation Timeout

**Applies to**: Layer 4 multi-level cascade simulation (PERF-CM-05, REL-CM-01)

**Implementation**:
- Hard timeout of 3 seconds (configurable via CASCADE_TIMEOUT_SECS)
- Timeout applies to cascade computation only, not the full Layer 4 evaluation
- On timeout: return results computed so far with `timed_out=True` flag
- Include warning in presentation: "Cascade simulation timed out at level N"
- This is graceful degradation, not a failure — partial results are still useful

```python
import time

def simulate_cascade(
    florida_order: dict,
    ohio_orders: list[dict],
    config: AgentConfig
) -> CascadeImpactResult:
    start = time.monotonic()
    impacted = []
    depth_reached = 0

    for depth in range(1, config.max_cascade_depth + 1):
        if time.monotonic() - start > config.cascade_timeout_secs:
            return CascadeImpactResult(
                impacted_orders=impacted,
                timed_out=True,
                max_depth_reached=depth - 1,
                warning=f"Cascade timed out at level {depth} of "
                        f"{config.max_cascade_depth}"
            )
        depth_reached = depth
        # ... cascade logic for this depth level ...

    return CascadeImpactResult(
        impacted_orders=impacted,
        timed_out=False,
        max_depth_reached=depth_reached
    )
```
