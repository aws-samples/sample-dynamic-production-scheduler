"""Tests for cross-cutting decorators."""

from __future__ import annotations

import pytest
from botocore.exceptions import ClientError
from pydantic import ValidationError

from audit_mcp.decorators import log_tool_invocation, tool_error_handler


@tool_error_handler
async def _raise_validation_error():
    raise ValidationError.from_exception_data("test", [])


@tool_error_handler
async def _raise_client_error_not_found():
    raise ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "not found"}},
        "GetItem",
    )


@tool_error_handler
async def _raise_client_error_other():
    raise ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "boom"}},
        "PutItem",
    )


@tool_error_handler
async def _raise_unexpected():
    raise RuntimeError("unexpected")


@tool_error_handler
@log_tool_invocation
async def _success_tool():
    return {"ok": True}


@pytest.mark.asyncio
async def test_validation_error_returns_invalid_input():
    result = await _raise_validation_error()
    assert result["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_client_error_not_found():
    result = await _raise_client_error_not_found()
    assert result["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_client_error_other_returns_internal():
    result = await _raise_client_error_other()
    assert result["error"]["code"] == "INTERNAL_ERROR"


@pytest.mark.asyncio
async def test_unexpected_error_returns_internal():
    result = await _raise_unexpected()
    assert result["error"]["code"] == "INTERNAL_ERROR"
    assert "unexpected" not in result["error"]["message"].lower()


@pytest.mark.asyncio
async def test_success_tool_returns_result():
    result = await _success_tool()
    assert result == {"ok": True}
