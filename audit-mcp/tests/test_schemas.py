"""Tests for Pydantic input validation schemas."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from audit_mcp.models.schemas import (
    GetAuditTrailInput,
    WriteAuditEntryInput,
)


class TestWriteAuditEntryInput:
    """Tests for WriteAuditEntryInput validation."""

    def test_valid_input(self):
        ts = datetime.now(timezone.utc).isoformat()
        inp = WriteAuditEntryInput(
            session_id="sess-001",
            agent="orchestrator",
            action="prioritize_order",
            details={"order_id": "FL-001"},
            timestamp=ts,
        )
        assert inp.session_id == "sess-001"
        assert inp.agent == "orchestrator"

    def test_various_agent_names_accepted(self):
        """Any non-empty string up to 128 chars is accepted as agent name."""
        ts = datetime.now(timezone.utc).isoformat()
        for agent in [
            "orchestrator",
            "impact_assessment",
            "capacity_optimization_agent",
            "constraint_matching_agent",
            "orchestrator_agent",
            "planner",
        ]:
            inp = WriteAuditEntryInput(
                session_id="s1",
                agent=agent,
                action="test",
                details={"k": "v"},
                timestamp=ts,
            )
            assert inp.agent == agent

    def test_empty_agent_rejected(self):
        ts = datetime.now(timezone.utc).isoformat()
        with pytest.raises(ValidationError):
            WriteAuditEntryInput(
                session_id="s1",
                agent="",
                action="test",
                details={"k": "v"},
                timestamp=ts,
            )

    def test_agent_too_long_rejected(self):
        ts = datetime.now(timezone.utc).isoformat()
        with pytest.raises(ValidationError):
            WriteAuditEntryInput(
                session_id="s1",
                agent="a" * 129,
                action="test",
                details={"k": "v"},
                timestamp=ts,
            )

    def test_empty_session_id_rejected(self):
        ts = datetime.now(timezone.utc).isoformat()
        with pytest.raises(ValidationError):
            WriteAuditEntryInput(
                session_id="",
                agent="planner",
                action="test",
                details={"k": "v"},
                timestamp=ts,
            )

    def test_empty_action_rejected(self):
        ts = datetime.now(timezone.utc).isoformat()
        with pytest.raises(ValidationError):
            WriteAuditEntryInput(
                session_id="s1",
                agent="planner",
                action="",
                details={"k": "v"},
                timestamp=ts,
            )

    def test_empty_details_rejected(self):
        ts = datetime.now(timezone.utc).isoformat()
        with pytest.raises(ValidationError):
            WriteAuditEntryInput(
                session_id="s1",
                agent="planner",
                action="test",
                details={},
                timestamp=ts,
            )

    def test_future_timestamp_rejected(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        with pytest.raises(ValidationError):
            WriteAuditEntryInput(
                session_id="s1",
                agent="planner",
                action="test",
                details={"k": "v"},
                timestamp=future,
            )

    def test_invalid_timestamp_format_rejected(self):
        with pytest.raises(ValidationError):
            WriteAuditEntryInput(
                session_id="s1",
                agent="planner",
                action="test",
                details={"k": "v"},
                timestamp="not-a-date",
            )

    def test_z_suffix_timestamp_accepted(self):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        inp = WriteAuditEntryInput(
            session_id="s1",
            agent="planner",
            action="test",
            details={"k": "v"},
            timestamp=ts,
        )
        assert inp.timestamp == ts


class TestGetAuditTrailInput:
    """Tests for GetAuditTrailInput validation."""

    def test_valid_session_only(self):
        inp = GetAuditTrailInput(session_id="sess-001")
        assert inp.session_id == "sess-001"
        assert inp.agent is None
        assert inp.start_time is None

    def test_valid_with_agent_filter(self):
        inp = GetAuditTrailInput(
            session_id="sess-001",
            agent="capacity_agent",
        )
        assert inp.agent == "capacity_agent"

    def test_valid_with_start_time(self):
        ts = datetime.now(timezone.utc).isoformat()
        inp = GetAuditTrailInput(session_id="sess-001", start_time=ts)
        assert inp.start_time == ts

    def test_empty_session_id_rejected(self):
        with pytest.raises(ValidationError):
            GetAuditTrailInput(session_id="")

    def test_invalid_start_time_rejected(self):
        with pytest.raises(ValidationError):
            GetAuditTrailInput(session_id="s1", start_time="bad-date")

    def test_invalid_agent_rejected(self):
        """Agent over 128 chars should be rejected."""
        with pytest.raises(ValidationError):
            GetAuditTrailInput(session_id="s1", agent="a" * 129)
