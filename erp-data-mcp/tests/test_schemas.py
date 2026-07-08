"""Tests for Pydantic input validation models."""

import pytest
from pydantic import ValidationError

from erp_data_mcp.models.schemas import (
    GetCustomersInput,
    GetMachineCapacityInput,
    GetMaterialsInput,
    GetOrderByIdInput,
    GetOrdersInput,
    GetRunningTrackerInput,
    UpdateOrderPriorityInput,
    UpdateOrderStatusInput,
    UpdateRunningTrackerInput,
)


class TestGetOrdersInput:
    def test_valid_florida(self):
        inp = GetOrdersInput(plant="Florida")
        assert inp.plant == "Florida"
        assert inp.status is None

    def test_valid_with_status(self):
        inp = GetOrdersInput(plant="Ohio", status="Active")
        assert inp.status == "Active"

    def test_invalid_plant(self):
        with pytest.raises(ValidationError):
            GetOrdersInput(plant="Texas")

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            GetOrdersInput(plant="Florida", status="Unknown")


class TestGetOrderByIdInput:
    def test_valid(self):
        inp = GetOrderByIdInput(order_id="PO-2026-001")
        assert inp.order_id == "PO-2026-001"

    def test_invalid_format(self):
        with pytest.raises(ValidationError):
            GetOrderByIdInput(order_id="INVALID")

    def test_invalid_missing_prefix(self):
        with pytest.raises(ValidationError):
            GetOrderByIdInput(order_id="2026-001")


class TestUpdateOrderPriorityInput:
    def test_valid_p1(self):
        inp = UpdateOrderPriorityInput(order_id="PO-2026-001", priority="P1")
        assert inp.priority == "P1"

    def test_valid_p3(self):
        inp = UpdateOrderPriorityInput(order_id="PO-2026-010", priority="P3")
        assert inp.priority == "P3"

    def test_invalid_priority(self):
        with pytest.raises(ValidationError):
            UpdateOrderPriorityInput(order_id="PO-2026-001", priority="P4")


class TestUpdateOrderStatusInput:
    def test_valid_transferred(self):
        inp = UpdateOrderStatusInput(order_id="PO-2026-001", status="Transferred")
        assert inp.status == "Transferred"

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            UpdateOrderStatusInput(order_id="PO-2026-001", status="Pending")


class TestGetMachineCapacityInput:
    def test_valid_rolling_mill(self):
        inp = GetMachineCapacityInput(machine_type="Rolling Mill")
        assert inp.machine_type == "Rolling Mill"

    def test_valid_finishing_line(self):
        inp = GetMachineCapacityInput(machine_type="Finishing Line")
        assert inp.machine_type == "Finishing Line"

    def test_invalid_machine(self):
        with pytest.raises(ValidationError):
            GetMachineCapacityInput(machine_type="Lathe")


class TestGetMaterialsInput:
    def test_valid_with_type(self):
        inp = GetMaterialsInput(material_type="Hot-Rolled Coil")
        assert inp.material_type == "Hot-Rolled Coil"

    def test_valid_no_filter(self):
        inp = GetMaterialsInput()
        assert inp.material_type is None

    def test_invalid_material(self):
        with pytest.raises(ValidationError):
            GetMaterialsInput(material_type="Copper Wire")


class TestGetCustomersInput:
    def test_valid_with_id(self):
        inp = GetCustomersInput(customer_id="CUST-1001")
        assert inp.customer_id == "CUST-1001"

    def test_valid_no_filter(self):
        inp = GetCustomersInput()
        assert inp.customer_id is None

    def test_invalid_customer_id(self):
        with pytest.raises(ValidationError):
            GetCustomersInput(customer_id="C-1001")


class TestGetRunningTrackerInput:
    def test_valid_uuid(self):
        inp = GetRunningTrackerInput(session_id="550e8400-e29b-41d4-a716-446655440000")
        assert inp.session_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_invalid_uuid(self):
        with pytest.raises(ValidationError):
            GetRunningTrackerInput(session_id="not-a-uuid")

    def test_invalid_uuid_version(self):
        # UUID v1 should fail (4th group must start with 4)
        with pytest.raises(ValidationError):
            GetRunningTrackerInput(session_id="550e8400-e29b-11d4-a716-446655440000")


class TestUpdateRunningTrackerInput:
    def test_valid_partial_update(self):
        inp = UpdateRunningTrackerInput(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            rolling_mill_normal_hrs=10.5,
        )
        assert inp.rolling_mill_normal_hrs == 10.5
        assert inp.finishing_line_normal_hrs is None

    def test_valid_add_transferred(self):
        inp = UpdateRunningTrackerInput(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            add_transferred="PO-2026-001",
        )
        assert inp.add_transferred == "PO-2026-001"

    def test_negative_hours_rejected(self):
        with pytest.raises(ValidationError):
            UpdateRunningTrackerInput(
                session_id="550e8400-e29b-41d4-a716-446655440000",
                rolling_mill_normal_hrs=-5.0,
            )

    def test_invalid_order_id_in_add(self):
        with pytest.raises(ValidationError):
            UpdateRunningTrackerInput(
                session_id="550e8400-e29b-41d4-a716-446655440000",
                add_transferred="INVALID",
            )
