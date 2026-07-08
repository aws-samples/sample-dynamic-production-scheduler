"""Unit tests for TrackerState singleton."""

from __future__ import annotations

import pytest

from constraint_matching_agent.models.schemas import (
    RunningCapacityTracker,
    RunningShiftHours,
)
from constraint_matching_agent.tracker import TrackerState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _shift(normal=100.0, ot=40.0, wk=20.0) -> RunningShiftHours:
    return RunningShiftHours(
        normal_hrs=normal, overtime_hrs=ot, weekend_hrs=wk,
        total_hrs=normal + ot + wk,
    )


def _make_tracker(**kw) -> RunningCapacityTracker:
    defaults = dict(
        session_id="test-session",
        rolling_mill_remaining_hrs=_shift(),
        finishing_line_remaining_hrs=_shift(),
        material_remaining_tons=500.0,
        workforce_remaining=50,
    )
    defaults.update(kw)
    return RunningCapacityTracker(**defaults)


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure singleton is clean before and after each test."""
    TrackerState.reset()
    yield
    TrackerState.reset()


# ---------------------------------------------------------------------------
# Singleton lifecycle
# ---------------------------------------------------------------------------


class TestSingletonLifecycle:
    def test_get_before_init_raises(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            TrackerState.get()

    def test_initialize_and_get(self):
        t = _make_tracker()
        TrackerState.initialize(t)
        state = TrackerState.get()
        assert state.tracker.session_id == "test-session"

    def test_initialize_replaces(self):
        TrackerState.initialize(_make_tracker(session_id="s1"))
        TrackerState.initialize(_make_tracker(session_id="s2"))
        assert TrackerState.get().tracker.session_id == "s2"

    def test_reset_clears(self):
        TrackerState.initialize(_make_tracker())
        TrackerState.reset()
        with pytest.raises(RuntimeError):
            TrackerState.get()


# ---------------------------------------------------------------------------
# consume_hours — tiered consumption (BR-CM-12)
# ---------------------------------------------------------------------------


class TestConsumeHours:
    def test_normal_only(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        rem = s.consume_hours("rolling_mill", 50.0)
        assert rem == 0.0
        hrs = s.tracker.rolling_mill_remaining_hrs
        assert hrs.normal_hrs == 50.0
        assert hrs.overtime_hrs == 40.0
        assert hrs.weekend_hrs == 20.0

    def test_spills_to_overtime(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        rem = s.consume_hours("rolling_mill", 120.0)
        assert rem == 0.0
        hrs = s.tracker.rolling_mill_remaining_hrs
        assert hrs.normal_hrs == 0.0
        assert hrs.overtime_hrs == 20.0
        assert hrs.weekend_hrs == 20.0

    def test_spills_to_weekend(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        rem = s.consume_hours("rolling_mill", 150.0)
        assert rem == 0.0
        hrs = s.tracker.rolling_mill_remaining_hrs
        assert hrs.normal_hrs == 0.0
        assert hrs.overtime_hrs == 0.0
        assert hrs.weekend_hrs == 10.0

    def test_insufficient_returns_remainder(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        rem = s.consume_hours("rolling_mill", 200.0)
        assert rem == 40.0  # 200 - 160 total
        hrs = s.tracker.rolling_mill_remaining_hrs
        assert hrs.total_hrs == 0.0

    def test_total_updated(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.consume_hours("finishing_line", 30.0)
        hrs = s.tracker.finishing_line_remaining_hrs
        assert hrs.total_hrs == pytest.approx(130.0)

    def test_zero_consumption(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        rem = s.consume_hours("rolling_mill", 0.0)
        assert rem == 0.0
        assert s.tracker.rolling_mill_remaining_hrs.normal_hrs == 100.0


# ---------------------------------------------------------------------------
# approve_order
# ---------------------------------------------------------------------------


class TestApproveOrder:
    def test_deducts_all_dimensions(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.approve_order("PO-2026-001", rm_hrs=10, fl_hrs=8,
                        material_tons=50, workforce=5)
        t = s.tracker
        assert t.rolling_mill_remaining_hrs.normal_hrs == 90.0
        assert t.finishing_line_remaining_hrs.normal_hrs == 92.0
        assert t.material_remaining_tons == 450.0
        assert t.workforce_remaining == 45
        assert "PO-2026-001" in t.orders_approved
        assert len(t.orders_processed) == 1
        assert t.orders_processed[0].decision == "approved"

    def test_material_floor_zero(self):
        TrackerState.initialize(_make_tracker(material_remaining_tons=10.0))
        s = TrackerState.get()
        s.approve_order("PO-2026-001", rm_hrs=0, fl_hrs=0,
                        material_tons=20, workforce=0)
        assert s.tracker.material_remaining_tons == 0.0

    def test_workforce_floor_zero(self):
        TrackerState.initialize(_make_tracker(workforce_remaining=3))
        s = TrackerState.get()
        s.approve_order("PO-2026-001", rm_hrs=0, fl_hrs=0,
                        material_tons=0, workforce=10)
        assert s.tracker.workforce_remaining == 0

    def test_multiple_approvals_cumulative(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.approve_order("PO-2026-001", 10, 10, 50, 5)
        s.approve_order("PO-2026-002", 10, 10, 50, 5)
        assert len(s.tracker.orders_approved) == 2
        assert len(s.tracker.orders_processed) == 2
        assert s.tracker.rolling_mill_remaining_hrs.normal_hrs == 80.0
        assert s.tracker.material_remaining_tons == 400.0


# ---------------------------------------------------------------------------
# reject_order
# ---------------------------------------------------------------------------


class TestRejectOrder:
    def test_no_capacity_change(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.reject_order("PO-2026-001")
        assert s.tracker.rolling_mill_remaining_hrs.normal_hrs == 100.0
        assert s.tracker.material_remaining_tons == 500.0
        assert "PO-2026-001" in s.tracker.orders_rejected
        assert s.tracker.orders_processed[0].decision == "rejected"

    def test_last_updated_set(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.reject_order("PO-2026-001")
        assert s.tracker.last_updated != ""


# ---------------------------------------------------------------------------
# skip_order + remove_from_skip_queue
# ---------------------------------------------------------------------------


class TestSkipOrder:
    def test_skip_adds_to_lists(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.skip_order("PO-2026-001")
        assert "PO-2026-001" in s.tracker.orders_skipped
        assert s.tracker.orders_processed[0].decision == "skipped"

    def test_skip_no_capacity_change(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.skip_order("PO-2026-001")
        assert s.tracker.rolling_mill_remaining_hrs.normal_hrs == 100.0

    def test_remove_from_skip_queue(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.skip_order("PO-2026-001")
        s.remove_from_skip_queue("PO-2026-001")
        assert "PO-2026-001" not in s.tracker.orders_skipped

    def test_remove_nonexistent_noop(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.remove_from_skip_queue("PO-2026-999")  # no error


# ---------------------------------------------------------------------------
# is_processed
# ---------------------------------------------------------------------------


class TestIsProcessed:
    def test_not_processed(self):
        TrackerState.initialize(_make_tracker())
        assert TrackerState.get().is_processed("PO-2026-001") is False

    def test_processed_after_approve(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.approve_order("PO-2026-001", 10, 8, 50, 5)
        assert s.is_processed("PO-2026-001") is True

    def test_processed_after_reject(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.reject_order("PO-2026-001")
        assert s.is_processed("PO-2026-001") is True

    def test_processed_after_skip(self):
        TrackerState.initialize(_make_tracker())
        s = TrackerState.get()
        s.skip_order("PO-2026-001")
        assert s.is_processed("PO-2026-001") is True
