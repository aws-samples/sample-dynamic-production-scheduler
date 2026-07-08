# NFR Design Patterns — Unit 7: Orchestrator Agent

## Pattern 1: Resilience — LLM Retry with Exponential Backoff

**Applies to**: All Bedrock InvokeModel calls (REL-OA-03)

**Implementation**: Same as Units 4-6. Strands SDK handles Bedrock retries internally.

```python
from strands import Agent
from strands.models.bedrock import BedrockModel

model = BedrockModel(
    model_id=settings.bedrock_model_id,
    max_tokens=8192,
    temperature=0,
    timeout=30
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
    max_retries=3
)
```

---

## Pattern 2: Resilience — Sub-Agent Failure with Partial Results

**Applies to**: Sub-agent tool calls via AgentCore API (REL-OA-01, BR-OA-08)

**Implementation**: Each sub-agent tool wraps the AgentCore invocation with retry and partial-result logic.

```python
@tool
def invoke_impact_assessment(prompt: str) -> str:
    """Invoke Impact Assessment Agent via AgentCore managed runtime."""
    for attempt in range(1 + settings.retry_limit):
        try:
            response = agentcore_client.invoke_agent(
                agent_id=settings.impact_assessment_agent_id,
                input_text=prompt,
                session_id=session.session_id
            )
            return response.output_text
        except Exception as e:
            if attempt < settings.retry_limit:
                logger.warning("Sub-agent failed, retrying",
                    extra={"agent": "impact_assessment", "attempt": attempt})
                continue
            logger.error("Sub-agent failed after retry",
                extra={"agent": "impact_assessment", "error": str(e)})
            session.error_log.append(AgentError(
                agent_id=settings.impact_assessment_agent_id,
                error_type="exception", message=str(e),
                retried=True, retry_succeeded=False
            ))
            return f"Impact Assessment Agent is unavailable: {str(e)}"
```

The LLM system prompt instructs the Orchestrator to handle partial results gracefully.

---

## Pattern 3: Orchestration — Hybrid Session State

**Applies to**: Session management across multi-round workflow (REL-OA-02, BR-OA-07)

**Implementation**: Strands conversation history for LLM context + explicit WorkflowSession for programmatic tracking.

```python
@dataclass
class WorkflowSession:
    session_id: str
    created_at: str
    current_phase: WorkflowPhase = WorkflowPhase.IDLE
    disruption_event: DisruptionEvent | None = None
    round1_complete: bool = False
    round2_complete: bool = False
    decisions: list[OrderDecision] = field(default_factory=list)
    what_if_count: int = 0
    error_log: list[AgentError] = field(default_factory=list)

    def transition(self, new_phase: WorkflowPhase) -> None:
        logger.info("Phase transition",
            extra={"old_phase": self.current_phase, "new_phase": new_phase})
        self.current_phase = new_phase

    def persist(self, memory_client) -> None:
        """Write session to AgentCore Memory for recovery."""
        try:
            memory_client.write(self.session_id, "workflow_session",
                                asdict(self))
        except Exception as e:
            logger.warning("Failed to persist session",
                extra={"error": str(e)})
```

---

## Pattern 4: Observability — Structured Agent Logging

**Applies to**: All agent operations (OBS-OA-01, OBS-OA-02, SECURITY-03)

**Implementation**: Same JSON logging pattern as Units 1-6.

```python
import logging
from pythonjsonlogger import jsonlogger

def configure_logging() -> logging.Logger:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"}
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger("orchestrator_agent")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

---

## Pattern 5: Security — Environment-Based Configuration

**Applies to**: All configurable parameters (SEC-OA-02, SECURITY-12)

```python
from pydantic_settings import BaseSettings

class OrchestratorSettings(BaseSettings):
    bedrock_model_id: str = "us.anthropic.claude-4-5-haiku-20250514-v1:0"
    mcp_gateway_url: str
    impact_assessment_agent_id: str
    capacity_optimization_agent_id: str
    constraint_matching_agent_id: str
    audit_mcp_url: str
    session_timeout_minutes: int = 60
    max_turns: int = 100
    retry_limit: int = 1
    log_level: str = "INFO"

    class Config:
        env_prefix = ""
```

---

## Pattern 6: Security — Input Validation

**Applies to**: Planner message validation (SEC-OA-01, SECURITY-05, BR-OA-15)

```python
from pydantic import BaseModel, Field, field_validator
import re

class PlannerMessage(BaseModel):
    text: str = Field(..., max_length=4000)
    session_id: str = Field(..., pattern=r"^[0-9a-f-]{36}$")

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        # Strip potential injection patterns
        return re.sub(r"<script[^>]*>.*?</script>", "", v, flags=re.IGNORECASE)
```

---

## Pattern 7: Resilience — Fail-Closed Agent Wrapper

**Applies to**: Agent entry point (SEC-OA-05, SECURITY-15)

```python
def run_agent(task: str, session_id: str) -> AgentResult:
    try:
        logger.info("Orchestrator invoked",
            extra={"session_id": session_id})
        result = agent(task)
        return AgentResult(success=True, output=str(result))
    except KeyboardInterrupt:
        logger.warning("Agent interrupted",
            extra={"session_id": session_id})
        return AgentResult(success=False,
            error="Orchestrator Agent was interrupted")
    except Exception as e:
        logger.error("Agent failed",
            extra={"session_id": session_id, "error": str(e)},
            exc_info=True)
        return AgentResult(success=False,
            error="Orchestrator Agent encountered an error")
```

---

## Pattern 8: Streaming — Hybrid Token Relay

**Applies to**: Streaming coordination (PERF-OA-04, BR-OA-09)

**Implementation**: Natural language tokens pass through directly; structured data sent as complete payloads.

```python
# System prompt excerpt for streaming behavior
STREAMING_PROMPT = """
Streaming Rules:
- When generating natural language responses, stream tokens normally.
- When presenting structured data (tables, capacity tracker, approval
  requests), format as a complete markdown block before sending.
- Always prefix sub-agent output with the agent name badge.
- Phase transition announcements are sent as structured payloads.
"""
```

The Strands SDK handles token-level streaming natively. The Orchestrator's callback function tags each token with the active agent name for frontend routing.
