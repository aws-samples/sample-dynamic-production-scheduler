"""Structured JSON logging configuration.

Outputs JSON to stdout — captured by AgentCore runtime and routed
to CloudWatch (Pattern 4, SECURITY-03).
"""

from __future__ import annotations

import logging

from pythonjsonlogger import jsonlogger


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the agent logger with JSON formatting."""
    logger = logging.getLogger("capacity_optimization_agent")

    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "agent_name",
        },
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
