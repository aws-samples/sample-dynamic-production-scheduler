"""Pydantic input validation models for audit MCP tools."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class WriteAuditEntryInput(BaseModel):
    """Input schema for write_audit_entry tool."""

    session_id: str = Field(..., min_length=1, max_length=128)
    agent: str = Field(..., min_length=1, max_length=128)
    action: str = Field(..., min_length=1, max_length=256)
    details: dict = Field(..., min_length=1)
    timestamp: str = Field(..., min_length=1)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO 8601 format and not in the future."""
        from datetime import datetime, timezone, timedelta

        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}") from exc
        now = datetime.now(timezone.utc)
        if parsed > now + timedelta(seconds=60):
            raise ValueError("Timestamp must not be in the future")
        return v


class GetAuditTrailInput(BaseModel):
    """Input schema for get_audit_trail tool."""

    session_id: str = Field(..., min_length=1, max_length=128)
    agent: Optional[str] = Field(None, max_length=128)
    start_time: Optional[str] = None

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: str | None) -> str | None:
        """Validate ISO 8601 format if provided."""
        if v is None:
            return v
        from datetime import datetime

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}") from exc
        return v
