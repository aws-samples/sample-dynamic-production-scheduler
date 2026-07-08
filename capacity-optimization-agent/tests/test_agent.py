"""Unit tests for agent.py — tool wrappers, create_agent, run_agent."""

from __future__ import annotations

import json
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from capacity_optimization_agent.agent import (
    AgentResult,
    PYTHON_TOOLS,
    _build_capacity_impact,
    _get_settings,
    compute_capacity_snapshot,
    filter_delay_candidates_tool,
    process_delay_decision,
    apply_constraint_tool,
    check_utilization_warnings_tool,
    run_agent,
)
from capacity_optimization_agent.config import AgentSettings


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _init_settings():
    """Populate module-level _settings for tool wrappers."""
    import capacity_optimization_agent.agent as mod
    mod._settings = AgentSettings(
        gateway_url="https://test-gateway.example.com",
    )
    mod._capacity_state = None
    yield
    mod._settings = None
    mod._capacity_state = None


def _sample_equipment() -> list[dict]:
    return [
        {
            "machine_type": "Rolling Mill",
            "total_hours_per_week": 120.0,
            "planned_downtime_hrs_week": 8.0,
            "net_available_hours_per_week": 112.0,
            "product_families": ["Steel Coil", "Steel Plate"],
        },
        {
            "machine_type": "Finishing Line",
            "total_hours_per_week": 100.0,
            "planned_downtime_hrs_week": 5.0,
            "net_available_hours_per_week": 95.0,
            "product_families": ["Steel Coil"],
        },
    ]


def _sample_orders() -> list[dict]:
    return [
        {
            "order_id": "PO-2026-001",
            "product_family": "Steel Coil",
            "customer_id": "CUST-001",
            "customer_tier": "Tier3",
            "due_date": "2026-04-15",
            "quantity": 50,
            "order_value": 80000.0,
            "priority": "P3",
            "rolling_mill_hours": 20.0,
            "finishing_line_hours": 10.0,
            "raw_material_tons": 25.0,
        },
    ]


def _sample_customers() -> dict:
    return {
        "CUST-001": {
            "customer_id": "CUST-001",
            "customer_name": "Test Corp",
            "customer_tier": "Tier3",
            "penalty_clause": False,
        },
    }


def _sample_workforce() -> dict:
    return {
        "total_operators": 20,
        "currently_allocated": 14,
        "available_surplus": 6,
        "operators_per_rolling_mill": 2,
        "operators_per_finishing_line": 1,
    }


def _sample_materials() -> list[dict]:
    return [
        {
            "material_type": "Hot Rolled Coil",
            "current_inventory_tons": 500.0,
            "committed_to_orders_tons": 300.0,
            "available_surplus_tons": 200.0,
            "product_families": ["Steel Coil"],
        },
    ]


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

class TestSettingsHelper:
    def test_get_settings_returns_settings(self):
        s = _get_settings()
        assert isinstance(s, AgentSettings)

    def test_get_settings_fails_when_not_initialized(self):
        import capacity_optimization_agent.agent as mod
        mod._settings = None
        with pytest.raises(AssertionError, match="Agent not initialized"):
            _get_settings()


# -------------------------------------------------------------------
# compute_capacity_snapshot tool
# -------------------------------------------------------------------

class TestComputeCapacitySnapshot:
    def test_returns_valid_snapshot(self):
        result_json = compute_capacity_snapshot.__wrapped__(
            equipment_json=json.dumps(_sample_equipment()),
            orders_json=json.dumps(_sample_orders()),
            customers_json=json.dumps(_sample_customers()),
            workforce_json=json.dumps(_sample_workforce()),
            materials_json=json.dumps(_sample_materials()),
        )
        result = json.loads(result_json)
        assert "equipment" in result
        assert "utilization" in result
        assert "bottleneck" in result
        assert "total_surplus_summary" in result
        assert len(result["equipment"]) == 2
        assert len(result["utilization"]) == 2

    def test_caches_state(self):
        import capacity_optimization_agent.agent as mod
        assert mod._capacity_state is None
        compute_capacity_snapshot.__wrapped__(
            equipment_json=json.dumps(_sample_equipment()),
            orders_json=json.dumps(_sample_orders()),
            customers_json=json.dumps(_sample_customers()),
            workforce_json=json.dumps(_sample_workforce()),
            materials_json=json.dumps(_sample_materials()),
        )
        assert mod._capacity_state is not None

    def test_accepts_customer_list_format(self):
        customers_list = [
            {"customer_id": "CUST-001", "customer_name": "Test", "customer_tier": "Tier3"},
        ]
        result_json = compute_capacity_snapshot.__wrapped__(
            equipment_json=json.dumps(_sample_equipment()),
            orders_json=json.dumps(_sample_orders()),
            customers_json=json.dumps(customers_list),
            workforce_json=json.dumps(_sample_workforce()),
            materials_json=json.dumps(_sample_materials()),
        )
        result = json.loads(result_json)
        assert "bottleneck" in result


# -------------------------------------------------------------------
# filter_delay_candidates_tool
# -------------------------------------------------------------------

class TestFilterDelayCandidatesTool:
    def _build_snapshot(self):
        """Helper: run compute_capacity_snapshot to populate cache."""
        compute_capacity_snapshot.__wrapped__(
            equipment_json=json.dumps(_sample_equipment()),
            orders_json=json.dumps(_sample_orders()),
            customers_json=json.dumps(_sample_customers()),
            workforce_json=json.dumps(_sample_workforce()),
            materials_json=json.dumps(_sample_materials()),
        )
        import capacity_optimization_agent.agent as mod
        return mod._capacity_state.snapshot

    def test_returns_candidates(self):
        snapshot = self._build_snapshot()
        orders_json = json.dumps(
            [o.model_dump() for o in snapshot.existing_load], default=str,
        )
        result_json = filter_delay_candidates_tool.__wrapped__(
            orders_json=orders_json,
            workforce_json=json.dumps(_sample_workforce()),
            bottleneck_machine="Rolling Mill",
        )
        result = json.loads(result_json)
        assert isinstance(result, list)


# -------------------------------------------------------------------
# _build_capacity_impact helper
# -------------------------------------------------------------------

class TestBuildCapacityImpact:
    def _build_snapshot(self):
        compute_capacity_snapshot.__wrapped__(
            equipment_json=json.dumps(_sample_equipment()),
            orders_json=json.dumps(_sample_orders()),
            customers_json=json.dumps(_sample_customers()),
            workforce_json=json.dumps(_sample_workforce()),
            materials_json=json.dumps(_sample_materials()),
        )
        import capacity_optimization_agent.agent as mod
        return mod._capacity_state

    def test_returns_correct_structure(self):
        state = self._build_snapshot()
        result = _build_capacity_impact(state)
        assert "senderPlant" in result
        assert "receiverPlant" in result
        sender = result["senderPlant"]
        receiver = result["receiverPlant"]
        assert sender["name"] == "Florida"
        assert receiver["name"] == "Ohio"
        for key in ("rollingMill", "finishingLine", "overall"):
            assert "current" in sender[key]
            assert "projected" in sender[key]
            assert "current" in receiver[key]
            assert "projected" in receiver[key]

    def test_sender_plant_always_zero(self):
        state = self._build_snapshot()
        result = _build_capacity_impact(state)
        sender = result["senderPlant"]
        for key in ("rollingMill", "finishingLine", "overall"):
            assert sender[key]["current"] == 0
            assert sender[key]["projected"] == 0

    def test_receiver_plant_uses_snapshot_utilization(self):
        state = self._build_snapshot()
        result = _build_capacity_impact(state)
        receiver = result["receiverPlant"]
        # Utilization should be non-negative
        assert receiver["rollingMill"]["current"] >= 0
        assert receiver["finishingLine"]["current"] >= 0
        assert receiver["overall"]["current"] >= 0

    def test_deterministic_same_state(self):
        state = self._build_snapshot()
        result1 = _build_capacity_impact(state)
        result2 = _build_capacity_impact(state)
        assert result1 == result2

    def test_custom_plant_names(self):
        state = self._build_snapshot()
        result = _build_capacity_impact(state, sender_plant="PlantA", receiver_plant="PlantB")
        assert result["senderPlant"]["name"] == "PlantA"
        assert result["receiverPlant"]["name"] == "PlantB"


# -------------------------------------------------------------------
# process_delay_decision tool
# -------------------------------------------------------------------

class TestProcessDelayDecision:
    def _build_snapshot(self):
        compute_capacity_snapshot.__wrapped__(
            equipment_json=json.dumps(_sample_equipment()),
            orders_json=json.dumps(_sample_orders()),
            customers_json=json.dumps(_sample_customers()),
            workforce_json=json.dumps(_sample_workforce()),
            materials_json=json.dumps(_sample_materials()),
        )

    def test_approve_updates_surplus(self):
        self._build_snapshot()
        florida_demand = {"Rolling Mill": 100.0, "Finishing Line": 60.0}
        result_json = process_delay_decision.__wrapped__(
            order_id="PO-2026-001",
            action="approve",
            florida_demand_json=json.dumps(florida_demand),
        )
        result = json.loads(result_json)
        assert result["action"] == "approve"
        assert "surplus_after" in result
        assert "capacityImpact" in result
        ci = result["capacityImpact"]
        assert ci["senderPlant"]["name"] == "Florida"
        assert ci["receiverPlant"]["name"] == "Ohio"
        assert ci["senderPlant"]["rollingMill"]["current"] == 0
        assert ci["senderPlant"]["overall"]["projected"] == 0
        assert isinstance(ci["receiverPlant"]["rollingMill"]["current"], (int, float))
        assert isinstance(ci["receiverPlant"]["overall"]["current"], (int, float))

    def test_reject_returns_unchanged(self):
        self._build_snapshot()
        florida_demand = {"Rolling Mill": 100.0, "Finishing Line": 60.0}
        result_json = process_delay_decision.__wrapped__(
            order_id="PO-2026-001",
            action="reject",
            florida_demand_json=json.dumps(florida_demand),
        )
        result = json.loads(result_json)
        assert result["action"] == "reject"
        assert "capacityImpact" in result

    def test_fails_without_cached_state(self):
        import capacity_optimization_agent.agent as mod
        mod._capacity_state = None
        with pytest.raises(AssertionError, match="No capacity snapshot"):
            process_delay_decision.__wrapped__(
                order_id="PO-2026-001",
                action="approve",
                florida_demand_json=json.dumps({}),
            )

    def test_unknown_order_returns_error(self):
        self._build_snapshot()
        result_json = process_delay_decision.__wrapped__(
            order_id="NONEXISTENT",
            action="approve",
            florida_demand_json=json.dumps({"Rolling Mill": 100.0}),
        )
        result = json.loads(result_json)
        assert "error" in result


# -------------------------------------------------------------------
# apply_constraint_tool
# -------------------------------------------------------------------

class TestApplyConstraintTool:
    def _build_snapshot(self):
        compute_capacity_snapshot.__wrapped__(
            equipment_json=json.dumps(_sample_equipment()),
            orders_json=json.dumps(_sample_orders()),
            customers_json=json.dumps(_sample_customers()),
            workforce_json=json.dumps(_sample_workforce()),
            materials_json=json.dumps(_sample_materials()),
        )

    def test_shift_restriction_zeroes_weekend(self):
        self._build_snapshot()
        florida_demand = {"Rolling Mill": 100.0, "Finishing Line": 60.0}
        result_json = apply_constraint_tool.__wrapped__(
            constraint_text="No weekend shifts",
            constraint_type="shift_restriction",
            florida_demand_json=json.dumps(florida_demand),
        )
        result = json.loads(result_json)
        assert "capacity_before" in result
        assert "capacity_after" in result
        after = result["capacity_after"]
        assert after["rolling_mill_weekend_hrs"] == 0.0
        assert after["finishing_line_weekend_hrs"] == 0.0
        assert "capacityImpact" in result
        ci = result["capacityImpact"]
        assert ci["senderPlant"]["name"] == "Florida"
        assert ci["receiverPlant"]["name"] == "Ohio"
        assert ci["senderPlant"]["rollingMill"]["current"] == 0
        assert isinstance(ci["receiverPlant"]["rollingMill"]["current"], (int, float))

    def test_capacity_limit_reduces_surplus(self):
        self._build_snapshot()
        florida_demand = {"Rolling Mill": 100.0, "Finishing Line": 60.0}
        result_json = apply_constraint_tool.__wrapped__(
            constraint_text="Cap all at 80%",
            constraint_type="capacity_limit",
            florida_demand_json=json.dumps(florida_demand),
        )
        result = json.loads(result_json)
        assert "bottleneck_after" in result
        assert "capacityImpact" in result

    def test_fails_without_cached_state(self):
        import capacity_optimization_agent.agent as mod
        mod._capacity_state = None
        with pytest.raises(AssertionError, match="No capacity snapshot"):
            apply_constraint_tool.__wrapped__(
                constraint_text="No overtime",
                constraint_type="shift_restriction",
                florida_demand_json=json.dumps({}),
            )


# -------------------------------------------------------------------
# check_utilization_warnings_tool
# -------------------------------------------------------------------

class TestCheckUtilizationWarningsTool:
    def test_returns_warnings_above_threshold(self):
        self._build_snapshot()
        import capacity_optimization_agent.agent as mod
        snapshot = mod._capacity_state.snapshot
        util_json = json.dumps(
            [u.model_dump() for u in snapshot.utilization], default=str,
        )
        result_json = check_utilization_warnings_tool.__wrapped__(
            utilization_json=util_json,
            warning_pct=0.01,  # very low threshold to trigger warnings
        )
        result = json.loads(result_json)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_no_warnings_below_threshold(self):
        self._build_snapshot()
        import capacity_optimization_agent.agent as mod
        snapshot = mod._capacity_state.snapshot
        util_json = json.dumps(
            [u.model_dump() for u in snapshot.utilization], default=str,
        )
        result_json = check_utilization_warnings_tool.__wrapped__(
            utilization_json=util_json,
            warning_pct=1.0,  # 100% threshold — nothing triggers
        )
        result = json.loads(result_json)
        assert result == []

    def _build_snapshot(self):
        compute_capacity_snapshot.__wrapped__(
            equipment_json=json.dumps(_sample_equipment()),
            orders_json=json.dumps(_sample_orders()),
            customers_json=json.dumps(_sample_customers()),
            workforce_json=json.dumps(_sample_workforce()),
            materials_json=json.dumps(_sample_materials()),
        )


# -------------------------------------------------------------------
# PYTHON_TOOLS list
# -------------------------------------------------------------------

class TestPythonToolsList:
    def test_contains_all_tools(self):
        assert len(PYTHON_TOOLS) == 6
        names = {t.__name__ for t in PYTHON_TOOLS}
        assert "stage_erp_data" in names
        assert "compute_capacity_snapshot" in names
        assert "filter_delay_candidates_tool" in names
        assert "process_delay_decision" in names
        assert "apply_constraint_tool" in names
        assert "check_utilization_warnings_tool" in names


# -------------------------------------------------------------------
# run_agent — fail-closed wrapper (Pattern 7)
# -------------------------------------------------------------------

class TestRunAgent:
    def test_success_path(self):
        mock_agent = MagicMock(return_value="capacity analysis done")
        result = run_agent(mock_agent, "Analyze Ohio capacity", "sess-001")
        assert result.success is True
        assert result.data == "capacity analysis done"
        mock_agent.assert_called_once_with("Analyze Ohio capacity")

    def test_fail_closed_on_exception(self):
        mock_agent = MagicMock(side_effect=RuntimeError("LLM timeout"))
        result = run_agent(mock_agent, "Analyze Ohio capacity", "sess-002")
        assert result.success is False
        assert "error" in result.error.lower()
        assert result.data is None
