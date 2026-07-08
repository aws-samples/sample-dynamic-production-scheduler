"""Tests for cross-cutting decorators."""

import pytest
from botocore.exceptions import ClientError
from pydantic import ValidationError

from erp_data_mcp.decorators import log_tool_invocation, tool_error_handler


@pytest.mark.asyncio
class TestToolErrorHandler:
    async def test_success_passthrough(self):
        @tool_error_handler
        async def good_tool():
            return {"data": "ok"}

        result = await good_tool()
        assert result == {"data": "ok"}

    async def test_validation_error_returns_invalid_input(self):
        @tool_error_handler
        async def bad_input_tool():
            raise ValidationError.from_exception_data(
                title="test",
                line_errors=[],
            )

        result = await bad_input_tool()
        assert result["error"]["code"] == "INVALID_INPUT"

    async def test_conditional_check_returns_invalid_transition(self):
        @tool_error_handler
        async def conditional_fail_tool():
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "fail"}},
                "UpdateItem",
            )

        result = await conditional_fail_tool()
        assert result["error"]["code"] == "INVALID_TRANSITION"

    async def test_resource_not_found_returns_not_found(self):
        @tool_error_handler
        async def not_found_tool():
            raise ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": "fail"}},
                "GetItem",
            )

        result = await not_found_tool()
        assert result["error"]["code"] == "NOT_FOUND"

    async def test_other_client_error_returns_internal(self):
        @tool_error_handler
        async def dynamo_error_tool():
            raise ClientError(
                {"Error": {"Code": "InternalServerError", "Message": "fail"}},
                "Query",
            )

        result = await dynamo_error_tool()
        assert result["error"]["code"] == "INTERNAL_ERROR"

    async def test_unexpected_error_returns_internal(self):
        @tool_error_handler
        async def crash_tool():
            raise RuntimeError("unexpected")

        result = await crash_tool()
        assert result["error"]["code"] == "INTERNAL_ERROR"
        assert "unexpected" not in result["error"]["message"]


@pytest.mark.asyncio
class TestLogToolInvocation:
    async def test_success_returns_result(self):
        @log_tool_invocation
        async def timed_tool():
            return {"result": 42}

        result = await timed_tool()
        assert result == {"result": 42}

    async def test_exception_propagates(self):
        @log_tool_invocation
        async def failing_tool():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await failing_tool()
