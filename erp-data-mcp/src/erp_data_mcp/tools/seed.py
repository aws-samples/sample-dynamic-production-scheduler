"""Seed data reset tool — wipes and reloads ERP data from seed definitions."""

from __future__ import annotations

import logging
from typing import Any

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.decorators import log_tool_invocation, tool_error_handler
from erp_data_mcp.seed.data import (
    CUSTOMERS,
    FLORIDA_ORDERS,
    MACHINE_CAPACITY,
    WORKFORCE,
    OHIO_ORDERS,
    RAW_MATERIALS,
)
from erp_data_mcp.seed.demo_data import (
    DEMO_CUSTOMERS,
    DEMO_FLORIDA_ORDERS,
    DEMO_MACHINE_CAPACITY,
    DEMO_WORKFORCE,
    DEMO_OHIO_ORDERS,
    DEMO_RAW_MATERIALS,
)

logger = logging.getLogger("erp_data_mcp")


def _clear_table(table) -> int:
    """Delete all items from a DynamoDB table. Returns count deleted."""
    scan = table.scan()
    items = scan.get("Items", [])
    key_schema = table.key_schema
    key_names = [k["AttributeName"] for k in key_schema]

    deleted = 0
    with table.batch_writer() as batch:
        for item in items:
            key = {k: item[k] for k in key_names}
            batch.delete_item(Key=key)
            deleted += 1

    # Handle pagination
    while scan.get("LastEvaluatedKey"):
        scan = table.scan(ExclusiveStartKey=scan["LastEvaluatedKey"])
        with table.batch_writer() as batch:
            for item in scan.get("Items", []):
                key = {k: item[k] for k in key_names}
                batch.delete_item(Key=key)
                deleted += 1

    return deleted


def _batch_write(table, items: list[dict]) -> int:
    """Write items to a DynamoDB table."""
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    return len(items)


@tool_error_handler
@log_tool_invocation
async def reset_seed_data(
    mode: str, settings: Settings, db: DynamoDBClient
) -> dict[str, Any]:
    """Wipe all ERP tables and reseed with fresh data.

    Args:
        mode: "demo" for curated 16-order subset, "full" for all 40 orders.
        settings: App settings with table names.
        db: DynamoDB client.

    Returns:
        Summary dict with counts per table and mode used.
    """
    if mode not in ("demo", "full"):
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"Invalid mode '{mode}'. Must be 'demo' or 'full'.",
            }
        }

    if mode == "demo":
        florida, ohio = DEMO_FLORIDA_ORDERS, DEMO_OHIO_ORDERS
        capacity, workforce, materials, customers = (
            DEMO_MACHINE_CAPACITY, DEMO_WORKFORCE, DEMO_RAW_MATERIALS, DEMO_CUSTOMERS,
        )
    else:
        florida, ohio = FLORIDA_ORDERS, OHIO_ORDERS
        capacity, workforce, materials, customers = (
            MACHINE_CAPACITY, WORKFORCE, RAW_MATERIALS, CUSTOMERS,
        )

    table_data_map = [
        (settings.dynamodb_table_orders, florida + ohio, "orders"),
        (settings.dynamodb_table_capacity, capacity, "machine_capacity"),
        (settings.dynamodb_table_workforce, workforce, "workforce"),
        (settings.dynamodb_table_materials, materials, "raw_materials"),
        (settings.dynamodb_table_customers, customers, "customers"),
    ]

    results = {"mode": mode, "tables": {}}

    for table_name, items, label in table_data_map:
        table = db.get_table(table_name)
        deleted = _clear_table(table)
        written = _batch_write(table, items)
        results["tables"][label] = {"deleted": deleted, "written": written}
        logger.info(f"Reset {label}: deleted {deleted}, wrote {written} into {table_name}")

    total_written = sum(t["written"] for t in results["tables"].values())
    results["total_written"] = total_written
    results["success"] = True
    results["message"] = (
        f"ERP data reset to {mode} mode: {len(florida)} Florida + {len(ohio)} Ohio orders "
        f"({total_written} total records across all tables)"
    )

    return results
