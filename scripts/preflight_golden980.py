#!/usr/bin/env python3
"""Read-only Golden980 preflight: exact 980 SKU; stable Prom UID; known suppliers.

This is an offline verification, NOT an import or publishing script.
Usage: python scripts/preflight_golden980.py
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/approved_golden980_2026-11-01.csv"
STAGED = ROOT / "data/golden980_complete_staging_pool.csv"
EXPECTED = {"SIGMA": 632, "ZAINSTRUMENTOM": 313, "GRANDINSTRUMENT": 35}

def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))

def main() -> int:
    approved, staged = load(MASTER), load(STAGED)
    errors = []
    m = {r["sku"]: r for r in approved}
    s = {r["sku"]: r for r in staged}
    for label, rows in [("master", approved), ("staging", staged)]:
        if len(rows) != 980 or len({r["sku"] for r in rows}) != 980:
            errors.append(f"{label} must contain 980 unique SKUs")
    if set(m) != set(s):
        errors.append(f"SKU difference: missing={len(set(m)-set(s))}, extra={len(set(s)-set(m))}")
    counts = dict(Counter(r["supplier"] for r in staged))
    if counts != EXPECTED:
        errors.append(f"supplier count mismatch: {counts}")
    if len({r["prom_uid"] for r in staged}) != 980:
        errors.append("Prom UID collision or missing UID")
    if any(not r["prom_group_id"] for r in staged):
        errors.append("Missing group mapping")
    if any(r["prom_uid"] != m[r["sku"]]["prom_uid"] for r in staged if r["sku"] in m):
        errors.append("Changed Prom UID")
    known = [r["external_id"] for r in staged if r["external_id"]]
    if len(set(known)) != len(known):
        errors.append("Duplicate known external IDs")
    unresolved = [r["sku"] for r in staged if not r["external_id"]]
    if len(unresolved) != 123:
        errors.append(f"Unexpected missing external IDs: {len(unresolved)}")
    print(f"Golden980 master={len(m)} staged={len(s)} suppliers={counts} "
          f"external_id_HOLD={len(unresolved)}")
    for error in errors:
        print("INVALID: " + error)
    if errors:
        return 2
    print("STRUCTURE PASS; PUBLISH HOLD until 123 external IDs are safely matched")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
