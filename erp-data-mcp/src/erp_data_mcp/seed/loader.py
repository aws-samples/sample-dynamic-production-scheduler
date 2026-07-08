"""Seed data loader — loads mock ERP data into DynamoDB tables.

Usage:
    python -m erp_data_mcp.seed.loader          # Full dataset (40 active orders)
    python -m erp_data_mcp.seed.loader --demo    # Demo subset (16 active orders)
"""

from __future__ import annotations

import logging
import sys

from erp_data_mcp.config import Settings
from erp_data_mcp.db.client import DynamoDBClient
from erp_data_mcp.logging_config import configure_logging
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


def _batch_write(table, items: list[dict]) -> int:
    """Write items to DynamoDB table using batch writer.

    Args:
        table: boto3 DynamoDB Table resource.
        items: List of item dicts to write.

    Returns:
        Number of items written.
    """
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    return len(items)


def seed_all(settings: Settings | None = None, *, demo: bool = False) -> None:
    """Load seed data into DynamoDB tables.

    Args:
        settings: Optional Settings override. Uses defaults if None.
        demo: If True, load the curated demo subset (16 active orders)
              instead of the full dataset (40 active orders).
    """
    if settings is None:
        settings = Settings()

    db = DynamoDBClient.get_instance(settings.aws_region)

    if demo:
        florida, ohio = DEMO_FLORIDA_ORDERS, DEMO_OHIO_ORDERS
        capacity, workforce, materials, customers = (
            DEMO_MACHINE_CAPACITY, DEMO_WORKFORCE, DEMO_RAW_MATERIALS, DEMO_CUSTOMERS,
        )
        mode = "DEMO"
    else:
        florida, ohio = FLORIDA_ORDERS, OHIO_ORDERS
        capacity, workforce, materials, customers = (
            MACHINE_CAPACITY, WORKFORCE, RAW_MATERIALS, CUSTOMERS,
        )
        mode = "FULL"

    logger.info(f"Seed mode: {mode} ({len(florida)} Florida + {len(ohio)} Ohio orders)")

    table_data_map = [
        (settings.dynamodb_table_orders, florida + ohio, "orders"),
        (settings.dynamodb_table_capacity, capacity, "machine_capacity"),
        (settings.dynamodb_table_workforce, workforce, "workforce"),
        (settings.dynamodb_table_materials, materials, "raw_materials"),
        (settings.dynamodb_table_customers, customers, "customers"),
    ]

    total = 0
    for table_name, items, label in table_data_map:
        table = db.get_table(table_name)
        count = _batch_write(table, items)
        logger.info(f"Seeded {count} {label} records into {table_name}")
        total += count

    logger.info(f"Seed complete ({mode}): {total} total records loaded")


def main() -> None:
    """CLI entry point for seed data loading.

    Usage:
        python -m erp_data_mcp.seed.loader          # Full dataset
        python -m erp_data_mcp.seed.loader --demo    # Demo subset
    """
    configure_logging("INFO")
    demo = "--demo" in sys.argv
    mode = "demo" if demo else "full"
    logger.info(f"Starting seed data load ({mode})...")
    try:
        seed_all(demo=demo)
        logger.info("Seed data load completed successfully")
    except Exception as exc:
        logger.error(f"Seed data load failed: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
