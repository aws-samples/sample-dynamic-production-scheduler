# Unit Test Instructions — Gateway Rework (Rework Cycle 2)

## Overview

Unit tests validate the Lambda handlers, CDK stacks, and gateway setup scripts in isolation.

## 1. Lambda Handler Unit Tests

### 1.1 ERP Data MCP Lambda Handler

Test file: `erp-data-mcp/tests/test_lambda_handler.py`

```python
"""Unit tests for erp-data-mcp Lambda handler."""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Mock DynamoDB before importing handler
with patch("erp_data_mcp.db.client.DynamoDBClient.get_instance", return_value=MagicMock()):
    from erp_data_mcp.lambda_handler import handler, TOOL_DISPATCH


class FakeContext:
    aws_request_id = "test-request-123"


@pytest.fixture
def context():
    return FakeContext()


def test_missing_tool_name(context):
    """Handler returns error when tool_name is missing."""
    result = handler({}, context)
    assert "error" in result
    assert "Missing tool_name" in result["error"]


def test_unknown_tool(context):
    """Handler returns error for unknown tool names."""
    result = handler({"tool_name": "nonexistent_tool"}, context)
    assert "error" in result
    assert "Unknown tool" in result["error"]


def test_tool_dispatch_registry():
    """All 10 ERP tools are registered in dispatch table."""
    expected_tools = [
        "get_orders_tool", "get_order_by_id_tool",
        "update_order_priority_tool", "update_order_status_tool",
        "get_machine_capacity_tool", "get_manpower_tool",
        "get_materials_tool", "get_customers_tool",
        "get_running_tracker_tool", "update_running_tracker_tool",
    ]
    for tool in expected_tools:
        assert tool in TOOL_DISPATCH, f"Missing tool: {tool}"
    assert len(TOOL_DISPATCH) == 10


@patch("erp_data_mcp.lambda_handler._handle_get_orders")
def test_successful_dispatch(mock_handler, context):
    """Handler dispatches to correct tool and returns result."""
    mock_handler.return_value = [{"order_id": "PO-2025-001"}]
    result = handler(
        {"tool_name": "get_orders_tool", "arguments": {"plant": "Florida"}},
        context,
    )
    assert "result" in result
    mock_handler.assert_called_once()


def test_validation_error(context):
    """Handler returns input validation error for bad arguments."""
    result = handler(
        {"tool_name": "get_order_by_id_tool", "arguments": {}},
        context,
    )
    assert "error" in result
    assert "Invalid input" in result["error"]


@patch("erp_data_mcp.lambda_handler._handle_get_orders", side_effect=RuntimeError("DB down"))
def test_internal_error_generic_message(mock_handler, context):
    """Handler returns generic error on internal failure (SECURITY-09)."""
    result = handler(
        {"tool_name": "get_orders_tool", "arguments": {"plant": "Florida"}},
        context,
    )
    assert result["error"] == "Internal server error"
    assert "DB down" not in json.dumps(result)


def test_name_field_fallback(context):
    """Handler accepts 'name' field as fallback for 'tool_name'."""
    result = handler({"name": "nonexistent_tool"}, context)
    assert "Unknown tool" in result["error"]
```

### 1.2 Audit MCP Lambda Handler

Test file: `audit-mcp/tests/test_lambda_handler.py`

```python
"""Unit tests for audit-mcp Lambda handler."""
import json
import pytest
from unittest.mock import patch, MagicMock

with patch("audit_mcp.db.client.DynamoDBClient.get_instance", return_value=MagicMock()):
    from audit_mcp.lambda_handler import handler, TOOL_DISPATCH


class FakeContext:
    aws_request_id = "test-request-456"


@pytest.fixture
def context():
    return FakeContext()


def test_missing_tool_name(context):
    result = handler({}, context)
    assert "Missing tool_name" in result["error"]


def test_unknown_tool(context):
    result = handler({"tool_name": "bad_tool"}, context)
    assert "Unknown tool" in result["error"]


def test_tool_dispatch_registry():
    """Both audit tools are registered."""
    assert "write_audit_entry_tool" in TOOL_DISPATCH
    assert "get_audit_trail_tool" in TOOL_DISPATCH
    assert len(TOOL_DISPATCH) == 2


@patch("audit_mcp.lambda_handler._handle_get_audit_trail")
def test_successful_dispatch(mock_handler, context):
    mock_handler.return_value = []
    result = handler(
        {"tool_name": "get_audit_trail_tool", "arguments": {"session_id": "abc"}},
        context,
    )
    assert "result" in result


@patch("audit_mcp.lambda_handler._handle_write_audit_entry", side_effect=Exception("fail"))
def test_internal_error_no_stack_trace(mock_handler, context):
    """No stack trace in error response (SECURITY-09)."""
    result = handler(
        {"tool_name": "write_audit_entry_tool", "arguments": {"session_id": "x", "agent": "a", "action": "b", "details": {}, "timestamp": "t"}},
        context,
    )
    assert result["error"] == "Internal server error"
```


### Run Lambda Handler Tests

```bash
# ERP Data MCP
cd erp-data-mcp
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pip install pytest
pytest tests/test_lambda_handler.py -v

# Audit MCP
cd ../audit-mcp
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pip install pytest
pytest tests/test_lambda_handler.py -v
```

Expected: All tests pass, 0 failures.

## 2. CDK Stack Unit Tests

### 2.1 CDK Snapshot/Synth Tests

Test file: `infrastructure/test/gateway-stacks.test.ts`

```typescript
import * as cdk from "aws-cdk-lib";
import { Template } from "aws-cdk-lib/assertions";
import { CognitoStack } from "../lib/cognito-stack";
import { McpLambdaStack } from "../lib/mcp-lambda-stack";
import { GatewayIamStack } from "../lib/gateway-iam-stack";
import { DatabaseStack } from "../lib/database-stack";

describe("CognitoStack", () => {
  test("creates User Pool, Resource Server, and App Client", () => {
    const app = new cdk.App();
    const stack = new CognitoStack(app, "TestCognito");
    const template = Template.fromStack(stack);

    template.resourceCountIs("AWS::Cognito::UserPool", 1);
    template.resourceCountIs("AWS::Cognito::UserPoolResourceServer", 1);
    template.resourceCountIs("AWS::Cognito::UserPoolClient", 1);
    template.resourceCountIs("AWS::Cognito::UserPoolDomain", 1);
  });
});

describe("McpLambdaStack", () => {
  test("creates two Lambda functions with IAM roles", () => {
    const app = new cdk.App();
    const db = new DatabaseStack(app, "TestDB");
    const stack = new McpLambdaStack(app, "TestMcpLambda", {
      tableArns: db.tableArns,
    });
    const template = Template.fromStack(stack);

    template.resourceCountIs("AWS::Lambda::Function", 2);
    template.resourceCountIs("AWS::IAM::Role", 2);
    template.resourceCountIs("AWS::Logs::LogGroup", 2);
  });

  test("Lambda functions use Python 3.11 runtime", () => {
    const app = new cdk.App();
    const db = new DatabaseStack(app, "TestDB2");
    const stack = new McpLambdaStack(app, "TestMcpLambda2", {
      tableArns: db.tableArns,
    });
    const template = Template.fromStack(stack);

    template.hasResourceProperties("AWS::Lambda::Function", {
      Runtime: "python3.11",
    });
  });
});

describe("GatewayIamStack", () => {
  test("creates gateway management role", () => {
    const app = new cdk.App();
    const stack = new GatewayIamStack(app, "TestGatewayIam", {
      erpDataLambdaArn: "arn:aws:lambda:us-east-1:123456789:function:erp",
      auditLambdaArn: "arn:aws:lambda:us-east-1:123456789:function:audit",
      cognitoUserPoolArn: "arn:aws:cognito-idp:us-east-1:123456789:userpool/test",
    });
    const template = Template.fromStack(stack);

    template.resourceCountIs("AWS::IAM::Role", 1);
  });
});
```

### Run CDK Tests

```bash
cd infrastructure
npm test
```

Expected: All tests pass including new gateway stack tests.


## 3. Gateway Script Validation

Gateway scripts cannot be fully unit-tested without AWS API access, but validate:

```bash
# Syntax check all Python scripts
python -m py_compile infrastructure/scripts/create_gateway.py
python -m py_compile infrastructure/scripts/create_erp_data_target.py
python -m py_compile infrastructure/scripts/create_audit_target.py
python -m py_compile infrastructure/scripts/gateway_observability.py
python -m py_compile infrastructure/scripts/cognito_credentials_provider.py
```

Expected: No syntax errors.

## Test Summary

| Component | Test Type | Test Count | Expected |
|-----------|-----------|------------|----------|
| erp-data-mcp Lambda handler | Unit | 7 | All pass |
| audit-mcp Lambda handler | Unit | 5 | All pass |
| CDK gateway stacks | Snapshot/assertion | 4 | All pass |
| Gateway scripts | Syntax validation | 5 | No errors |