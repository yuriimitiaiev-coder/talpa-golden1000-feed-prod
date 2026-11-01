#!/usr/bin/env python3
"""Verify the post-import Golden980 identity export before any feed switchover.

Usage:
    python scripts/verify_golden980_bindings.py \
        data/approved_golden980_2026-11-01.csv /path/to/fresh_normalized_prom_export.csv

The fresh CSV must contain columns sku,prom_uid,external_id. Read-only.
Return code 0 = PASS; 2 = HOLD. Neither Prom nor the production feed is edited.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def read_rows(path: str) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"sku", "prom_uid", "external_id"}.issubset(reader.fieldnames or []):
            raise ValueError(f"{path}: required sku,prom_uid,external_id")
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]


def audit(master_file: str, latest_file: str) -> tuple[bool, list[str]]:
    master = read_rows(master_file)
    latest = read_rows(latest_file)
    problems: list[str] = []
    if len(master) != 980 or len(latest) != 980:
        problems.append(f"row count master={len(master)}, latest={len(latest)}")
    expected_skus = [r["sku"] for r in master]
    observed_skus = [r["sku"] for r in latest]
    if len(set(expected_skus)) != 980 or len(set(observed_skus)) != 980:
        problems.append("duplicate or missing SKU")
    expected = {r["sku"]: r for r in master}
    actual = {r["sku"]: r for r in latest}
    if set(expected) != set(actual):
        problems.append(
            f"SKU mismatch missing={sorted(set(expected)-set(actual))} "
            f"extra={sorted(set(actual)-set(expected))}"
        )
    obs_ids = [r["external_id"] for r in latest]
    if not all(obs_ids) or len(set(obs_ids)) != len(obs_ids):
        problems.append("empty or duplicate external IDs after binding")
    for sku in sorted(set(expected) & set(actual)):
        old = expected[sku]
        new = actual[sku]
        if old["prom_uid"] != new["prom_uid"]:
            problems.append(f"{sku}: Prom UID changed")
        wanted = old["external_id"] or old["prom_uid"]
        if new["external_id"] != wanted:
            problems.append(f"{sku}: external id expected={wanted} actual={new['external_id']}")
    return not problems, problems


def main(args: list[str]) -> int:
    if len(args) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        passed, problems = audit(args[1], args[2])
    except Exception as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2
    if passed:
        print("PASS: 980 approved SKU, 980 stable Prom UID, 980 unique external IDs")
        return 0
    for problem in problems[:60]:
        print("HOLD: " + problem, file=sys.stderr)
    print(f"HOLD: total violations={len(problems)}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
