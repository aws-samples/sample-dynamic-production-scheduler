# NFR Design Patterns — Unit 4: Impact Assessment Agent

## Pattern 1: Resilience — LLM Retry with Exponential Backoff

**Applies to**: All Bedrock InvokeModel calls (REL-IA-03)

**Implementation**:
- Strands SDK handles Bedrock retries internally
- Configure retry behavior via SDK agent config
- Retryable: ThrottlingException (backoff 1s, 2s, 4s — 3 attempts max)
- Non-retryable: ModelErrorException, ValidationException
- Timeout: 20 seconds per LLM call

```python
# Pattern: Strands agent with retry config
from strands import Agent
from strands.models.bedrock import BedrockModel

model = BedrockModel(
    model_id=settings.bedrock_model_id,
    max_tokens=4096,
    temperature=0,  # Deterministic scoring (REL-IA-04)
    timeout=20
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=mcp_tools,
    max_retries=3
)
```

---

## Pattern 2: Resilience — MCP Tool Failure Handling

**Applies to**: All MCP tool calls via HTTP/SSE (REL-IA-01)

**Implementation**:
- Agent system prompt instructs LLM on failure behavior per BR-IA-12/13
- get_orders failure: agent halts, returns error message to Orchestrator
- get_customers failure: agent proceeds with default tier scores (50)
- write_audit_entry failure: agent logs warning, continues
- update_order_priority failure: retry once via LLM re-invocation

```python
# Pattern: system prompt excerpt for failure handling
FAILURE_HANDLING_PROMPT = """
Tool Failure Rules:
- If get_orders returns an error: STOP immediately. Report the error.
- If get_customers returns an error: Continue scoring. Use 50 for all
  customer_tier scores. Include warning in your summary.
- If write_audit_entry returns an error: Log warning, continue workflow.
- If update_order_priority returns an error: Retry once. If still fails,
  report partial failure with list of orders that were not updated.
"""
```

---

## Pattern 3: Performance — Scoring Algorithm as Pure Python

**Applies to**: Priority scoring computation (PERF-IA-01, PERF-IA-03)

**Implementation**:
- Scoring algorithm implemented as pure Python functions (no LLM calls)
- LLM orchestrates tool calls and presentation; scoring is deterministic code
- This keeps the LLM budget for tool orchestration and natural language generation
- Scoring 20 orders takes < 1ms (negligible vs LLM and MCP latency)

```python
# Pattern: pure Python scoring (not LLM-driven)
def score_orders(
    orders: list[OrderInput],
    customers: dict[str, CustomerInput],
    weights: ScoringWeights,
    thresholds: PriorityThresholds
) -> list[ScoredOrder]:
    """Deterministic scoring — no LLM involved."""
    min_val = min(o.order_value for o in orders)
    max_val = max(o.order_value for o in orders)

    scored = []
    for order in orders:
        scores = CriterionScores(
            urgency=compute_urgency_score(order.due_date),
            customer_tier=compute_tier_score(order.customer_tier),
            order_value=compute_value_score(order.order_value, min_val, max_val),
            machine_complexity=compute_complexity_score(order.machine_types_required)
        )
        weighted = (
            scores.urgency * weights.urgency
            + scores.customer_tier * weights.customer_tier
            + scores.order_value * weights.order_value
            + scores.machine_complexity * weights.machine_complexity
        )
        priority = classify(weighted, thresholds)
        scored.append(ScoredOrder(order=order, scores=scores,
                                   weighted_score=weighted, priority=priority))
    return sorted(scored, key=sort_key)
```

The agent exposes `score_orders` as a Python tool that the LLM calls after fetching data via MCP tools. This hybrid approach (LLM for orchestration + Python for computation) maximizes both accuracy and speed.

---

## Pattern 4: Observability — Structured Agent Logging

**Applies to**: All agent operations (OBS-IA-01, OBS-IA-02, SECURITY-03)

**Implementation**:
- JSON-formatted logging to stdout (captured by AgentCore runtime)
- Log every MCP tool call: tool name, duration, success/failure
- Log classification results: order count, P1/P2/P3 distribution
- Log reclassification events: order_id, old/new priority
- Correlation via session_id

```python
# Pattern: agent logging setup
import logging
from pythonjsonlogger import jsonlogger

def configure_agent_logging():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"}
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger("impact_assessment_agent")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

---

## Pattern 5: Security — Environment-Based Agent Configuration

**Applies to**: All configurable parameters (SEC-IA-02, SECURITY-12)

**Implementation**:
- Bedrock model ID, MCP Gateway URL, scoring weights, thresholds from environment
- No hardcoded credentials or resource identifiers
- Pydantic Settings for validation at startup

```python
# Pattern: agent configuration
from pydantic_settings import BaseSettings

class AgentSettings(BaseSettings):
    bedrock_model_id: str = "us.anthropic.claude-4-5-haiku-20250514-v1:0"
    mcp_gateway_url: str
    weight_urgency: float = 0.40
    weight_customer_tier: float = 0.25
    weight_order_value: float = 0.20
    weight_machine_complexity: float = 0.15
    p1_threshold: int = 75
    p2_threshold: int = 50
    log_level: str = "INFO"

    class Config:
        env_prefix = ""
```

---

## Pattern 6: Security — Input Validation on Agent Entry Points

**Applies to**: Reclassification requests from Orchestrator (SEC-IA-01, SECURITY-05)

**Implementation**:
- Pydantic models validate all inputs before processing
- order_id format validated (PO-YYYY-NNN regex)
- priority enum validated (P1/P2/P3 only)
- MCP tool responses validated via Pydantic before scoring

```python
# Pattern: reclassification input validation
from pydantic import BaseModel, Field

class ReclassifyInput(BaseModel):
    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    new_priority: str = Field(..., pattern="^(P1|P2|P3)$")
```

---

## Pattern 7: Resilience — Fail-Closed Agent Wrapper

**Applies to**: Agent entry point (SEC-IA-05, SECURITY-15)

**Implementation**:
- Global exception handler wraps agent invocation
- On unhandled exception: return error to Orchestrator, do not proceed
- No partial results on failure (classification is all-or-nothing)

```python
# Pattern: fail-closed agent wrapper
async def run_agent(task: str, session_id: str) -> AgentResult:
    try:
        logger.info("Agent invoked", extra={
            "agent": "impact_assessment_agent",
            "session_id": session_id
        })
        result = await agent(task)
        return AgentResult(success=True, data=result)
    except Exception as e:
        logger.error("Agent failed", extra={
            "agent": "impact_assessment_agent",
            "session_id": session_id,
            "error": str(e)
        }, exc_info=True)
        return AgentResult(
            success=False,
            error="Impact Assessment Agent encountered an error"
        )
```
