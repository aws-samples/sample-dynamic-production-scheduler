"""Pydantic input validation models for all MCP tools."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class GetOrdersInput(BaseModel):
    """Input for get_orders tool."""

    plant: str = Field(..., pattern=r"^(Florida|Ohio)$", description="Plant name")
    status: Optional[str] = Field(
        None,
        pattern=r"^(Active|Delayed|Transferred|Cancelled)$",
        description="Optional status filter",
    )


class GetOrderByIdInput(BaseModel):
    """Input for get_order_by_id tool."""

    order_id: str = Field(
        ..., pattern=r"^PO-\d{4}-\d{3}$", description="Order ID (e.g., PO-2026-001)"
    )


class UpdateOrderPriorityInput(BaseModel):
    """Input for update_order_priority tool."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    priority: str = Field(..., pattern=r"^(P1|P2|P3)$", description="Priority level")


class UpdateOrderStatusInput(BaseModel):
    """Input for update_order_status tool."""

    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    status: str = Field(
        ...,
        pattern=r"^(Active|Delayed|Transferred|Cancelled)$",
        description="New status",
    )


class GetMachineCapacityInput(BaseModel):
    """Input for get_machine_capacity tool."""

    machine_type: str = Field(
        ...,
        pattern=r"^(Rolling Mill|Finishing Line)$",
        description="Machine type",
    )


class GetMaterialsInput(BaseModel):
    """Input for get_materials tool."""

    material_type: Optional[str] = Field(
        None,
        pattern=r"^(Hot-Rolled Coil|Steel Slab|Steel Billet)$",
        description="Optional material type filter",
    )


class GetCustomersInput(BaseModel):
    """Input for get_customers tool."""

    customer_id: Optional[str] = Field(
        None,
        pattern=r"^CUST-\d{4}$",
        description="Optional customer ID filter",
    )


class ResetSeedDataInput(BaseModel):
    """Input for reset_seed_data tool."""

    mode: str = Field(
        ...,
        pattern=r"^(demo|full)$",
        description="Seed mode: 'demo' for curated 16-order subset, 'full' for all 40 orders",
    )


class GetRunningTrackerInput(BaseModel):
    """Input for get_running_tracker tool."""

    session_id: str = Field(..., description="Workflow session ID (UUID v4)")

    @field_validator("session_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate session_id is a valid UUID v4."""
        pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not pattern.match(v):
            raise ValueError("Invalid UUID v4 format for session_id")
        return v


class UpdateRunningTrackerInput(BaseModel):
    """Input for update_running_tracker tool."""

    session_id: str = Field(..., description="Workflow session ID (UUID v4)")
    rolling_mill_normal_hrs: Optional[float] = Field(None, ge=0)
    rolling_mill_overtime_hrs: Optional[float] = Field(None, ge=0)
    rolling_mill_weekend_hrs: Optional[float] = Field(None, ge=0)
    finishing_line_normal_hrs: Optional[float] = Field(None, ge=0)
    finishing_line_overtime_hrs: Optional[float] = Field(None, ge=0)
    finishing_line_weekend_hrs: Optional[float] = Field(None, ge=0)
    material_surplus_tons: Optional[dict[str, float]] = None
    workforce_surplus: Optional[float] = Field(None, ge=0)
    add_transferred: Optional[str] = Field(
        None, pattern=r"^PO-\d{4}-\d{3}$", description="Order ID to add to transferred list"
    )
    add_delayed: Optional[str] = Field(
        None, pattern=r"^PO-\d{4}-\d{3}$", description="Order ID to add to delayed list"
    )
    add_rejected: Optional[str] = Field(
        None, pattern=r"^PO-\d{4}-\d{3}$", description="Order ID to add to rejected list"
    )

    @field_validator("session_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate session_id is a valid UUID v4."""
        pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not pattern.match(v):
            raise ValueError("Invalid UUID v4 format for session_id")
        return v
