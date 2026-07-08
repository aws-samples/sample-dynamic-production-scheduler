"""Running Capacity Tracker — module-level singleton (Pattern 8).

Maintains running capacity state across order decisions.
Tiered hour consumption: normal -> overtime -> weekend (BR-CM-12).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from constraint_matching_agent.models.schemas import (
    ProcessedOrderEntry,
    RunningCapacityTracker,
    RunningShiftHours,
)

logger = logging.getLogger("constraint_matching_agent")


class TrackerState:
    """Module-level singleton for running capacity tracker."""

    _instance: TrackerState | None = None

    def __init__(self, tracker: RunningCapacityTracker) -> None:
        self._tracker = tracker

    @classmethod
    def initialize(cls, tracker: RunningCapacityTracker) -> TrackerState:
        """Create or replace the singleton instance."""
        cls._instance = cls(tracker)
        return cls._instance

    @classmethod
    def get(cls) -> TrackerState:
        """Return the singleton. Raises if not initialized."""
        if cls._instance is None:
            raise RuntimeError("TrackerState not initialized")
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Clear singleton (for testing)."""
        cls._instance = None

    @property
    def tracker(self) -> RunningCapacityTracker:
        return self._tracker

    def is_processed(self, order_id: str) -> bool:
        """Check if order was already processed."""
        return any(
            e.order_id == order_id for e in self._tracker.orders_processed
        )

    def consume_hours(
        self, machine: str, required_hrs: float,
    ) -> float:
        """Tiered consumption: normal -> overtime -> weekend (BR-CM-12).

        Returns remaining hours (should be 0 if Layer 3 passed).
        """
        hrs: RunningShiftHours = getattr(
            self._tracker, f"{machine}_remaining_hrs",
        )
        remaining = required_hrs

        normal_consumed = min(hrs.normal_hrs, remaining)
        hrs.normal_hrs -= normal_consumed
        remaining -= normal_consumed

        if remaining > 0:
            ot_consumed = min(hrs.overtime_hrs, remaining)
            hrs.overtime_hrs -= ot_consumed
            remaining -= ot_consumed

        if remaining > 0:
            wk_consumed = min(hrs.weekend_hrs, remaining)
            hrs.weekend_hrs -= wk_consumed
            remaining -= wk_consumed

        hrs.total_hrs = hrs.normal_hrs + hrs.overtime_hrs + hrs.weekend_hrs
        return remaining

    def approve_order(
        self,
        order_id: str,
        rm_hrs: float,
        fl_hrs: float,
        material_tons: float,
        workforce: int,
        recommendation_category: str = "",
    ) -> None:
        """Deduct capacity for an approved order (BR-CM-09)."""
        self.consume_hours("rolling_mill", rm_hrs)
        self.consume_hours("finishing_line", fl_hrs)
        self._tracker.material_remaining_tons = max(
            self._tracker.material_remaining_tons - material_tons, 0.0,
        )
        self._tracker.workforce_remaining = max(
            self._tracker.workforce_remaining - workforce, 0,
        )
        self._tracker.orders_approved.append(order_id)
        now = datetime.now(timezone.utc).isoformat()
        self._tracker.orders_processed.append(ProcessedOrderEntry(
            order_id=order_id,
            decision="approved",
            recommendation_category=recommendation_category,
            rolling_mill_hrs_consumed=rm_hrs,
            finishing_line_hrs_consumed=fl_hrs,
            material_tons_consumed=material_tons,
            decided_at=now,
        ))
        self._tracker.last_updated = now
        logger.info("Order approved", extra={
            "order_id": order_id, "rm_hrs": rm_hrs,
            "fl_hrs": fl_hrs, "material_tons": material_tons,
        })

    def reject_order(
        self, order_id: str, recommendation_category: str = "",
    ) -> None:
        """Mark order as rejected — no capacity change (BR-CM-09)."""
        self._tracker.orders_rejected.append(order_id)
        now = datetime.now(timezone.utc).isoformat()
        self._tracker.orders_processed.append(ProcessedOrderEntry(
            order_id=order_id,
            decision="rejected",
            recommendation_category=recommendation_category,
            decided_at=now,
        ))
        self._tracker.last_updated = now
        logger.info("Order rejected", extra={"order_id": order_id})

    def skip_order(self, order_id: str) -> None:
        """Mark order as skipped — no capacity change (BR-CM-11)."""
        self._tracker.orders_skipped.append(order_id)
        now = datetime.now(timezone.utc).isoformat()
        self._tracker.orders_processed.append(ProcessedOrderEntry(
            order_id=order_id,
            decision="skipped",
            decided_at=now,
        ))
        self._tracker.last_updated = now
        logger.info("Order skipped", extra={"order_id": order_id})

    def remove_from_skip_queue(self, order_id: str) -> None:
        """Remove order from skip list on revisit (BR-CM-11)."""
        if order_id in self._tracker.orders_skipped:
            self._tracker.orders_skipped.remove(order_id)
