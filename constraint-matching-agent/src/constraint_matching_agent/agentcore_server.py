"""AgentCore-compatible agent entry point.

Uses BedrockAgentCoreApp wrapper for deployment on
Bedrock AgentCore Managed Runtime.
"""

from __future__ import annotations

import os
import sys

# Ensure the src/ directory is on sys.path so package imports resolve
_src_dir = os.path.join(os.path.dirname(__file__), os.pardir)
if os.path.abspath(_src_dir) not in sys.path:
    sys.path.insert(0, os.path.abspath(_src_dir))

import json  # noqa: E402
import logging  # noqa: E402
import uuid  # noqa: E402

from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: E402

logger = logging.getLogger("constraint_matching_agent")

app = BedrockAgentCoreApp()

# Lazy-init to stay within 30s cold-start budget
_settings_cached = None
_factory_ready = False


def _ensure_factory():
    """One-time initialization of settings. Agent created per-request."""
    global _factory_ready, _settings_cached
    if _factory_ready:
        return
    from constraint_matching_agent.config import AgentSettings
    from constraint_matching_agent.logging_config import configure_logging

    _settings_cached = AgentSettings()
    configure_logging(_settings_cached.log_level)
    _factory_ready = True


def _create_agent_per_request(session_id: str = ""):
    """Create a fresh Strands Agent per invocation for memory isolation."""
    _ensure_factory()
    from constraint_matching_agent.agent import create_agent
    return create_agent(_settings_cached, session_id=session_id)


def _extract_structured_output(result) -> dict | None:
    """Extract structured output from an AgentResult.

    Tries ``model_dump()`` on the raw Strands result first (Pydantic model
    returned by ``structured_output_model``).  Falls back to JSON-parsing
    ``result.data`` if the raw object is unavailable.

    Returns the dict on success, or ``None`` if extraction fails.
    """
    # 1. Prefer the raw Pydantic model stored by run_agent
    raw = getattr(result, "raw_output", None)
    if raw is not None:
        if hasattr(raw, "model_dump"):
            try:
                return raw.model_dump()
            except Exception:
                logger.warning("model_dump() failed on raw_output", exc_info=True)

    # 2. Fallback: parse result.data as JSON
    data = getattr(result, "data", None)
    if data is not None:
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    logger.warning("Could not extract structured output from agent result")
    return None


@app.entrypoint
def invoke(payload, context):
    """Handle AgentCore invocation requests."""
    try:
        prompt = payload.get("prompt", "")
        # Prefer runtimeSessionId from AgentCore context (set via header),
        # fall back to payload session_id, then generate a new one.
        session_id = (
            getattr(context, "session_id", None)
            or payload.get("session_id")
            or str(uuid.uuid4())
        )

        logger.info(
            "AgentCore invoke received",
            extra={"session_id": session_id, "prompt_length": len(prompt)},
        )

        from constraint_matching_agent.agent import run_agent

        agent = _create_agent_per_request(session_id=session_id)
        result = run_agent(agent, prompt, session_id)

        if result.success:
            # Extract structured output from Strands agent result
            structured_output = _extract_structured_output(result)
            response = {"result": result.data, "session_id": session_id}
            if structured_output is not None:
                response["structured_output"] = structured_output
            return response
        else:
            return {
                "error": result.error,
                "session_id": session_id,
                "success": False,
            }
    except Exception as e:
        logger.error("Unhandled error in invoke", exc_info=True)
        return {
            "error": f"Internal error: {type(e).__name__}",
            "session_id": payload.get("session_id", "unknown"),
            "success": False,
        }


if __name__ == "__main__":
    app.run()
