"""Cross-cutting decorators for MCP tool handlers."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable

from botocore.exceptions import ClientError
from pydantic import ValidationError

logger = logging.getLogger("erp_data_mcp")


def log_tool_invocation(func: Callable) -> Callable:
    """Decorator that logs tool invocation timing and outcome.

    Captures start time, logs invocation, measures duration, and logs
    completion or failure with duration_ms.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        logger.info("Tool invoked", extra={"tool": func.__name__})
        try:
            result = await func(*args, **kwargs)
            duration_ms = round((time.monotonic() - start) * 1000, 2)
            logger.info(
                "Tool completed",
                extra={"tool": func.__name__, "duration_ms": duration_ms},
            )
            return result
        except Exception as exc:
            duration_ms = round((time.monotonic() - start) * 1000, 2)
            logger.error(
                "Tool failed",
                extra={
                    "tool": func.__name__,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            )
            raise

    return wrapper


def tool_error_handler(func: Callable) -> Callable:
    """Decorator that catches exceptions and returns standardized error responses.

    Maps known exceptions to error codes:
    - ValidationError -> INVALID_INPUT
    - ClientError (ConditionalCheckFailedException) -> INVALID_TRANSITION
    - ClientError (ResourceNotFoundException) -> NOT_FOUND
    - ClientError (other) -> INTERNAL_ERROR
    - Exception -> INTERNAL_ERROR (no stack trace leaked)
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except ValidationError as exc:
            logger.warning(
                "Input validation failed",
                extra={"tool": func.__name__, "error": str(exc)},
            )
            return {"error": {"code": "INVALID_INPUT", "message": str(exc)}}
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code == "ConditionalCheckFailedException":
                logger.warning(
                    "Status transition rejected",
                    extra={"tool": func.__name__},
                )
                return {
                    "error": {
                        "code": "INVALID_TRANSITION",
                        "message": "Status transition not allowed",
                    }
                }
            if error_code == "ResourceNotFoundException":
                return {"error": {"code": "NOT_FOUND", "message": "Resource not found"}}
            logger.error(
                "DynamoDB error",
                extra={"tool": func.__name__, "error": str(exc)},
            )
            return {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}
        except Exception as exc:
            logger.error(
                "Unexpected error",
                extra={"tool": func.__name__, "error": str(exc)},
                exc_info=True,
            )
            return {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}

    return wrapper
