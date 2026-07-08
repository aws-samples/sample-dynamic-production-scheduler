"""Unit tests for agent.py — tool wrappers, create_agent, run_agent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from constraint_matching_agent.agent import (
    AgentResult,
    PYTHON_TOOLS,
    _get_config,
    evaluate_funnel_tool,
    simulate_cascade_tool,
    record_decision_tool,
    run_agent,
)
from constraint_matching_agent.config import AgentSettings
from constraint_matching_agent.models.schemas import (
    AgentConfig,
    RunningCapacityTracker,
    RunningShiftHours,
)
from constraint_matching_agent.tracker import TrackerState


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _init_settings():
    """Populate module-level _settings for tool wrappers."""
    import constraint_matching_agent.agent as mod
    mod._settings = AgentSettings(
        gateway_url="https://test-gateway.example.com",
    )
    yield
    mod._settings = None


@pytest.fixture(autouse=True)
def _reset_tracker():
    """Reset TrackerState singleton between tests."""
    yield
    TrackerState.reset()


def _make_tracker() -> RunningCapacityTracker:
    """Create a tracker with known capacity for testing."""
    return RunningCapacityTracker(
        session_id="test-session",
        rolling_mill_remaining_hrs=RunningShiftHours(
            normal_hrs=100, overtime_hrs=20, weekend_hrs=10, total_hrs=130,
        ),
        finishing_line_remaining_hrs=RunningShiftHours(
            normal_hrs=80, overtime_hrs=15, weekend_hrs=8, total_hrs=103,
        ),
        material_remaining_tons=500.0,
        workforce_remaining=10,
    )


def _sample_order() -> dict:
    """Minimal Florida order dict."""
    return {
        "order_id": "PO-2026-001",
        "product_family": "Steel Coil",
        "customer_id": "CUST-FL-001",
        "customer_tier": "Tier1",
        "due_date": "2026-05-01",
        "quantity": 100,
        "order_value": 200000.0,
        "priority": "P1",
        "machine_types_required": ["Rolling Mill", "Finishing Line"],
        "rolling_mill_hours": 10.0,
        "finishing_line_hours": 5.0,
        "raw_material_tons": 50.0,
        "gauge": 0.5,
    }


def _sample_equipment() -> list[dict]:
    return [{
        "machine_type": "Rolling Mill",
        "gauge_range_min": 0.1,
        "gauge_range_max": 2.0,
        "supported_families": ["Steel Coil"],
        "setup_time_by_family": {"Steel Coil": 1.0},
    }, {
        "machine_type": "Finishing Line",
        "gauge_range_min": 0.1,
        "gauge_range_max": 2.0,
        "supported_families": ["Steel Coil"],
        "setup_time_by_family": {"Steel Coil": 0.5},
    }]


def _sample_materials() -> dict:
    return {
        "Steel Coil": {
            "available_tons": 600.0,
            "committed_tons": 100.0,
            "procurement_lead_time_days": 14,
        },
    }


def _sample_workforce() -> dict:
    return {
        "operators_available": 10,
        "operators_per_machine": {"Rolling Mill": 2, "Finishing Line": 1},
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
# Settings helper
# -------------------------------------------------------------------

class TestGetConfig:
    def test_returns_agent_config(self):
        c = _get_config()
        assert isinstance(c, AgentConfig)
        assert abs(c.utilization_warning_pct - 0.90) < 0.001

    def test_fails_when_not_initialized(self):
        import constraint_matching_agent.agent as mod
        mod._settings = None
        with pytest.raises(AssertionError, match="Agent not initialized"):
            _get_config()


# -------------------------------------------------------------------
# PYTHON_TOOLS list
# -------------------------------------------------------------------

class TestPythonToolsList:
    def test_contains_all_tools(self):
        assert len(PYTHON_TOOLS) == 4
        names = {t.__name__ for t in PYTHON_TOOLS}
        assert names == {
            "stage_erp_data",
            "evaluate_funnel_tool",
            "simulate_cascade_tool",
            "record_decision_tool",
        }


# -------------------------------------------------------------------
# evaluate_funnel_tool
# -------------------------------------------------------------------

class TestEvaluateFunnelTool:
    def test_returns_funnel_result_json(self):
        tracker = _make_tracker()
        config = AgentConfig()
        result_json = evaluate_funnel_tool.__wrapped__(
            order_json=json.dumps(_sample_order()),
            equipment_json=json.dumps(_sample_equipment()),
            materials_json=json.dumps(_sample_materials()),
            workforce_json=json.dumps(_sample_workforce()),
            receiving_plant_orders_json=json.dumps([]),
            tracker_json=json.dumps(tracker.model_dump()),
            config_json=json.dumps(config.model_dump()),
        )
        result = json.loads(result_json)
        assert result["order_id"] == "PO-2026-001"
        assert "layer1_equipment" in result
        assert "layer2_material" in result
        assert "layer3_utilization" in result
        assert "layer4_cascade" in result
        assert "recommendation_category" in result

    def test_equipment_failure_stops_early(self):
        order = _sample_order()
        order["gauge"] = 999.0  # out of range
        tracker = _make_tracker()
        config = AgentConfig()
        result_json = evaluate_funnel_tool.__wrapped__(
            order_json=json.dumps(order),
            equipment_json=json.dumps(_sample_equipment()),
            materials_json=json.dumps(_sample_materials()),
            workforce_json=json.dumps(_sample_workforce()),
            receiving_plant_orders_json=json.dumps([]),
            tracker_json=json.dumps(tracker.model_dump()),
            config_json=json.dumps(config.model_dump()),
        )
        result = json.loads(result_json)
        assert result["layer1_equipment"]["passed"] is False
        assert result["recommendation_category"] == "Non-transferable"


# -------------------------------------------------------------------
# simulate_cascade_tool
# -------------------------------------------------------------------

class TestSimulateCascadeTool:
    def test_returns_cascade_result_json(self):
        config = AgentConfig()
        result_json = simulate_cascade_tool.__wrapped__(
            order_json=json.dumps(_sample_order()),
            receiving_plant_orders_json=json.dumps([]),
            config_json=json.dumps(config.model_dump()),
        )
        result = json.loads(result_json)
        assert result["passed"] is True
        assert result["total_orders_impacted"] == 0

    def test_with_ohio_orders(self):
        ohio = [{
            "order_id": "PO-2026-050",
            "product_family": "Steel Coil",
            "customer_id": "CUST-OH-001",
            "customer_tier": "Tier2",
            "due_date": "2026-05-10",
            "rolling_mill_hours": 8.0,
            "finishing_line_hours": 4.0,
            "slack_days": 2,
        }]
        config = AgentConfig()
        result_json = simulate_cascade_tool.__wrapped__(
            order_json=json.dumps(_sample_order()),
            receiving_plant_orders_json=json.dumps(ohio),
            config_json=json.dumps(config.model_dump()),
        )
        result = json.loads(result_json)
        assert "impacted_orders" in result


# -------------------------------------------------------------------
# record_decision_tool
# -------------------------------------------------------------------

class TestRecordDecisionTool:
    def _init_tracker(self):
        TrackerState.initialize(_make_tracker())

    def test_approve_updates_tracker(self):
        self._init_tracker()
        result_json = record_decision_tool.__wrapped__(
            order_id="PO-2026-001",
            action="approve",
            rm_hrs=10.0,
            fl_hrs=5.0,
            material_tons=50.0,
            workforce=2,
            recommendation_category="Transfer",
        )
        result = json.loads(result_json)
        assert result["action"] == "approve"
        assert result["tracker_summary"]["approved"] == 1
        assert result["tracker_summary"]["rm_remaining"] == 120.0

    def test_reject_no_capacity_change(self):
        self._init_tracker()
        record_decision_tool.__wrapped__(
            order_id="PO-2026-001",
            action="reject",
            recommendation_category="Non-transferable",
        )
        state = TrackerState.get()
        assert state.tracker.rolling_mill_remaining_hrs.total_hrs == 130.0
        assert len(state.tracker.orders_rejected) == 1

    def test_skip_records_order(self):
        self._init_tracker()
        result_json = record_decision_tool.__wrapped__(
            order_id="PO-2026-001",
            action="skip",
        )
        result = json.loads(result_json)
        assert result["action"] == "skip"
        assert result["tracker_summary"]["skipped"] == 1

    def test_invalid_action_returns_error(self):
        self._init_tracker()
        result_json = record_decision_tool.__wrapped__(
            order_id="PO-2026-001",
            action="invalid",
        )
        result = json.loads(result_json)
        assert "error" in result


# -------------------------------------------------------------------
# run_agent — fail-closed wrapper (Pattern 7)
# -------------------------------------------------------------------

class TestRunAgent:
    def test_success_path(self):
        mock_agent = MagicMock(return_value="matching done")
        result = run_agent(mock_agent, "Match orders", "sess-001")
        assert result.success is True
        assert result.data == "matching done"
        mock_agent.assert_called_once_with("Match orders")

    def test_fail_closed_on_exception(self):
        mock_agent = MagicMock(side_effect=RuntimeError("LLM timeout"))
        result = run_agent(mock_agent, "Match orders", "sess-002")
        assert result.success is False
        assert "error" in result.error.lower()
        assert result.data is None

    def test_fail_closed_on_keyboard_interrupt(self):
        mock_agent = MagicMock(side_effect=Exception("interrupted"))
        result = run_agent(mock_agent, "Match orders", "sess-003")
        assert result.success is False
        assert result.error is not None
