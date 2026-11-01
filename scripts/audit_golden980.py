#!/usr/bin/env python3
"""Read-only comparison of the approved TALPA Golden980 export with the existing pool.

Usage:
    python scripts/audit_golden980.py /path/to/TALPA_GOLDEN980_MASTER_01-11-2026.csv

This tool deliberately NEVER edits a pool, a published feed, or Prom.ua.
It refuses to call a legacy 983/17 pool equivalent to the approved 980/20.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pool_common import load_pool


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/audit_golden980.py <approved_master.csv>", file=sys.stderr)
        return 2
    master_path = Path(argv[1])
    with master_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"sku", "prom_uid", "external_id"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing required columns: {sorted(required)}")
        approved = list(reader)
    sku = [(r.get("sku") or "").strip() for r in approved]
    uid = [(r.get("prom_uid") or "").strip() for r in approved]
    if len(sku) != 980 or len(set(sku)) != 980 or not all(sku):
        raise ValueError("Expected exactly 980 distinct, nonblank approved SKUs")
    if len(set(uid)) != 980 or not all(uid):
        raise ValueError("Expected 980 distinct, nonblank Prom unique identifiers")

    pool = load_pool()
    active = [r for r in pool if r["status"] == "ACTIVE"]
    reserve = [r for r in pool if r["status"] == "RESERVE"]
    active_set = {r["sku"] for r in active}
    master_set = set(sku)

    overlap = master_set & active_set
    report = {
        "master": master_path.name,
        "master_count": len(sku),
        "master_unique_prom_uid": len(set(uid)),
        "current_active": len(active),
        "current_reserve": len(reserve),
        "current_pool": len(pool),
        "configured_reserve": len(reserve),
        "unconfigured_free_slots": 1000 - len(pool),
        "reserve_capacity": 1000 - len(active),
        "unchanged_active": len(overlap),
        "approved_missing_from_active": sorted(master_set - active_set),
        "legacy_active_not_approved": sorted(active_set - master_set),
        "missing_external_ids_in_export": sum(
            not (r.get("external_id") or "").strip() for r in approved
        ),
        "missing_prom_offer_ids_in_legacy_active": sum(
            not (r.get("prom_offer_id") or "").strip() for r in active
        ),
        "legacy_supplier_counts": dict(Counter(r["supplier"] for r in active)),
        "safe_to_publish": active_set == master_set and len(active) == 980 and len(pool) <= 1000,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["safe_to_publish"]:
        print("HOLD: The approved Golden980 is not yet the production feed pool.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
