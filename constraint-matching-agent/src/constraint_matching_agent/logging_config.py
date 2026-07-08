"""Structured JSON logging configuration (Pattern 4).

Outputs JSON-formatted logs to stdout, captured by AgentCore runtime
and forwarded to CloudWatch.
"""

from __future__ import annotations

import logging

from pythonjsonlogger import jsonlogger


def configure_logging(level: str = "INFO") -> None:
    """Configure JSON logging for the agent."""
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger("constraint_matching_agent")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
