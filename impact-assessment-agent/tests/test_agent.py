"""Unit tests for agent.py — tool wrappers, create_agent, run_agent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from impact_assessment_agent.agent import (
    AgentResult,
    PYTHON_TOOLS,
    _get_thresholds,
    _get_weights,
    run_agent,
    score_orders_tool,
    reclassify_order_tool,
    get_priority_summary,
    explain_classification,
    get_group_tables,
)
from impact_assessment_agent.config import AgentSettings
from impact_assessment_agent.models.schemas import (
    CriterionScores,
    ScoredOrder,
    ScoringWeights,
    PriorityThresholds,
)


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _init_settings():
    """Populate module-level _settings for tool wrappers."""
    import impact_assessment_agent.agent as mod
    mod._settings = AgentSettings(
        gateway_url="https://test-gateway.example.com",
    )
    yield
    mod._settings = None


def _sample_order(
    order_id: str = "PO-2026-001",
    due_date: str = "2026-04-01",
    tier: str = "Tier1",
    value: float = 200000.0,
    machines: list[str] | None = None,
) -> dict:
    """Return a minimal raw order dict."""
    return {
        "order_id": order_id,
        "product_family": "Steel Coil",
        "customer_id": "CUST-001",
        "customer_tier": tier,
        "due_date": due_date,
        "quantity": 100,
        "order_value": value,
        "machine_types_required": machines or ["Rolling Mill", "Finishing Line"],
        "rolling_mill_hours": 10.0,
        "finishing_line_hours": 5.0,
        "raw_material_tons": 50.0,
    }


def _sample_customers() -> dict:
    return {
        "CUST-001": {
            "customer_id": "CUST-001",
            "customer_name": "Acme Manufacturing",
            "customer_tier": "Tier1",
        }
    }


# -------------------------------------------------------------------
# AgentResult
# -------------------------------------------------------------------

class TestAgentResult:
    def test_success_result(self):
        r = AgentResult(success=True, data="ok")
        assert r.success is True
        assert r.data == "ok"
        assert r.error is None

    def test_error_result(self):
        r = AgentResult(success=False, error="boom")
        assert r.success is False
        assert r.error == "boom"


# -------------------------------------------------------------------
# Settings helpers
# -------------------------------------------------------------------

class TestSettingsHelpers:
    def test_get_weights_returns_scoring_weights(self):
        w = _get_weights()
        assert isinstance(w, ScoringWeights)
        assert abs(w.urgency - 0.40) < 0.001

    def test_get_thresholds_returns_priority_thresholds(self):
        t = _get_thresholds()
        assert isinstance(t, PriorityThresholds)
        assert t.p1 == 75

    def test_get_weights_fails_when_not_initialized(self):
        import impact_assessment_agent.agent as mod
        mod._settings = None
        with pytest.raises(AssertionError, match="Agent not initialized"):
            _get_weights()


# -------------------------------------------------------------------
# Python tool wrappers
# -------------------------------------------------------------------

class TestScoreOrdersTool:
    def test_scores_single_order(self):
        orders = [_sample_order()]
        customers = _sample_customers()
        result_json = score_orders_tool.__wrapped__(
            orders_json=json.dumps(orders),
            customers_json=json.dumps(customers),
        )
        result = json.loads(result_json)
        assert len(result) == 1
        assert result[0]["order_id"] == "PO-2026-001"
        assert result[0]["priority"] in ("P1", "P2", "P3")

    def test_accepts_customer_list_format(self):
        orders = [_sample_order()]
        customers_list = [
            {"customer_id": "CUST-001", "customer_name": "Acme", "customer_tier": "Tier1"}
        ]
        result_json = score_orders_tool.__wrapped__(
            orders_json=json.dumps(orders),
            customers_json=json.dumps(customers_list),
        )
        result = json.loads(result_json)
        assert len(result) == 1


class TestReclassifyOrderTool:
    def test_reclassify_changes_priority(self):
        orders = [_sample_order()]
        customers = _sample_customers()
        scored_json = score_orders_tool.__wrapped__(
            orders_json=json.dumps(orders),
            customers_json=json.dumps(customers),
        )
        result_json = reclassify_order_tool.__wrapped__(
            scored_orders_json=scored_json,
            order_id="PO-2026-001",
            new_priority="P3",
        )
        result = json.loads(result_json)
        assert result["overridden"]["priority"] == "P3"
        assert result["overridden"]["manually_classified"] is True


class TestGetPrioritySummary:
    def test_returns_summary(self):
        orders = [_sample_order()]
        customers = _sample_customers()
        scored_json = score_orders_tool.__wrapped__(
            orders_json=json.dumps(orders),
            customers_json=json.dumps(customers),
        )
        summary_json = get_priority_summary.__wrapped__(scored_orders_json=scored_json)
        summary = json.loads(summary_json)
        assert summary["total_orders"] == 1
        assert "summary_text" in summary


class TestExplainClassification:
    def test_returns_explanation(self):
        orders = [_sample_order()]
        customers = _sample_customers()
        scored_json = score_orders_tool.__wrapped__(
            orders_json=json.dumps(orders),
            customers_json=json.dumps(customers),
        )
        scored = json.loads(scored_json)
        expl_json = explain_classification.__wrapped__(
            scored_order_json=json.dumps(scored[0])
        )
        expl = json.loads(expl_json)
        assert expl["order_id"] == "PO-2026-001"
        assert "explanation_text" in expl


class TestGetGroupTables:
    def test_returns_three_groups(self):
        orders = [_sample_order()]
        customers = _sample_customers()
        scored_json = score_orders_tool.__wrapped__(
            orders_json=json.dumps(orders),
            customers_json=json.dumps(customers),
        )
        tables_json = get_group_tables.__wrapped__(scored_orders_json=scored_json)
        tables = json.loads(tables_json)
        assert len(tables) == 3
        priorities = {t["priority"] for t in tables}
        assert priorities == {"P1", "P2", "P3"}


# -------------------------------------------------------------------
# PYTHON_TOOLS list
# -------------------------------------------------------------------

class TestPythonToolsList:
    def test_contains_all_tools(self):
        assert len(PYTHON_TOOLS) == 6
        names = {t.__name__ for t in PYTHON_TOOLS}
        assert "stage_erp_data" in names
        assert "score_orders_tool" in names
        assert "reclassify_order_tool" in names
        assert "get_priority_summary" in names
        assert "explain_classification" in names
        assert "get_group_tables" in names


# -------------------------------------------------------------------
# run_agent — fail-closed wrapper (Pattern 7)
# -------------------------------------------------------------------

class TestRunAgent:
    def test_success_path(self):
        mock_agent = MagicMock(return_value="classification done")
        result = run_agent(mock_agent, "Analyze orders", "sess-001")
        assert result.success is True
        assert result.data == "classification done"
        mock_agent.assert_called_once_with("Analyze orders")

    def test_fail_closed_on_exception(self):
        mock_agent = MagicMock(side_effect=RuntimeError("LLM timeout"))
        result = run_agent(mock_agent, "Analyze orders", "sess-002")
        assert result.success is False
        assert "error" in result.error.lower()
        assert result.data is None
