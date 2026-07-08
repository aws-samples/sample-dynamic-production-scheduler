"""Demo seed data — curated subset of 16 active orders (8 Florida + 8 Ohio).

Covers every workflow path and edge case with ~40% of the full dataset:
- All 3 urgency bands (urgent / medium / later)
- All 4 product families (Sheets, Coils, Plates, Bars)
- All 3 customer tiers
- Equipment incompatibility (Layer 1 fail)
- Material availability constraint (Layer 2 fail)
- Capacity/schedule overload (Layer 3 fail)
- Tiebreaker logic (same due date)
- Priority algorithm edge case (high-value Tier3)
- Delay candidates, committed orders, immovable orders
- Penalty clause customers
- Single-machine and dual-machine orders

Historical orders (H01-H04, H11-H14) are kept for background context.
Machine capacity, workforce, materials, and customers are identical to full set.
"""

from erp_data_mcp.seed.data import (
    CUSTOMERS,
    FLORIDA_ORDERS,
    MACHINE_CAPACITY,
    WORKFORCE,
    OHIO_ORDERS,
    RAW_MATERIALS,
)

# --- Florida subset (8 of 20 active + all historical) ---
_DEMO_FLORIDA_IDS = {
    # Urgent band
    "PO-2026-001",  # Baseline happy path: Tier1, Sheets, dual-machine, due 3/17
    "PO-2026-002",  # Tier1, Coils, Rolling Mill only — single-machine path
    "PO-2026-003",  # Steel Plates — equipment incompatibility (Layer 1 fail)
    # Medium band
    "PO-2026-005",  # Steel Plates, raw_material > surplus — Layer 2 fail
    "PO-2026-006",  # Same due date as 005 — tiebreaker test
    "PO-2026-007",  # High machine hours (65h) — Layer 3 capacity fail
    "PO-2026-010",  # Tier3, material constraint in medium window
    # Later band
    "PO-2026-015",  # Tier3 but $520K — priority algorithm edge case
}

# --- Ohio subset (8 of 20 active + all historical) ---
_DEMO_OHIO_IDS = {
    # Delay candidates (due 6+ weeks)
    "PO-2026-021",  # Tier3, Sheets, dual-machine — basic delay candidate
    "PO-2026-022",  # Tier3, Coils, Rolling Mill only — single-machine delay
    "PO-2026-024",  # Tier2 — borderline delay candidate
    # Committed (due 2-6 weeks)
    "PO-2026-026",  # Tier1, penalty clause (CUST-1001)
    "PO-2026-028",  # Tier1, penalty clause (CUST-1002)
    "PO-2026-030",  # >50% Rolling Mill capacity — capacity crunch
    # Immovable (due <2 weeks)
    "PO-2026-036",  # Tier1, cannot move
    "PO-2026-038",  # Tier2, cannot move
}


DEMO_FLORIDA_ORDERS: list[dict] = [
    o for o in FLORIDA_ORDERS if o["order_id"] in _DEMO_FLORIDA_IDS
]

DEMO_OHIO_ORDERS: list[dict] = [
    o for o in OHIO_ORDERS if o["order_id"] in _DEMO_OHIO_IDS
]

# Reference data stays the same — no trimming needed
DEMO_MACHINE_CAPACITY = MACHINE_CAPACITY
DEMO_WORKFORCE = WORKFORCE
DEMO_RAW_MATERIALS = RAW_MATERIALS
DEMO_CUSTOMERS = CUSTOMERS
