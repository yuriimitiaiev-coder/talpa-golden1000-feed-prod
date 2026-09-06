#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = ROOT / "sources" / "kit_pricing_skus.csv"
OUTPUT_JSON = ROOT / "docs" / "kit_price_snapshot.json"

SUPPORTED_PARTNERS = {"SIGMA", "ZAINSTRUMENTOM", "GRANDINSTRUMENT"}


def positive_number(text: str | None) -> float | None:
    raw = (text or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def load_targets() -> list[dict[str, str]]:
    if not SOURCE_CSV.exists():
        raise SystemExit(f"Missing KIT pricing source list: {SOURCE_CSV}")

    targets: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    with SOURCE_CSV.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"partner", "sku"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise SystemExit(
                f"{SOURCE_CSV.name} must contain columns: {sorted(required)}"
            )

        for raw in reader:
            partner = (raw.get("partner") or "").strip().upper()
            sku = (raw.get("sku") or "").strip()

            if not partner or not sku:
                continue
            if partner not in SUPPORTED_PARTNERS:
                raise SystemExit(f"Unsupported KIT pricing partner: {partner}")
            key = (partner, sku)
            if key in seen:
                raise SystemExit(f"Duplicate KIT pricing target: {partner}/{sku}")
            seen.add(key)
            targets.append({"partner": partner, "sku": sku})

    if not targets:
        raise SystemExit("KIT pricing target list is empty")

    return targets


def quantity_for(source, partner: str, available: bool) -> int:
    if not available:
        return 0

    raw = (source.findtext("quantity_in_stock") or "").strip()
    if raw:
        try:
            return max(int(float(raw.replace(",", "."))), 0)
        except ValueError:
            pass

    # Some feeds expose only availability, not an exact numeric stock.
    # 1 means "available; exact quantity is not machine-readable".
    return 1


def write_kit_price_snapshot(
    sigma_map,
    za_map,
    grand_map,
    za_adjustments: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    targets = load_targets()
    za_adjustments = za_adjustments or []
    za_adjusted = {item["sku"] for item in za_adjustments}

    maps = {
        "SIGMA": sigma_map,
        "ZAINSTRUMENTOM": za_map,
        "GRANDINSTRUMENT": grand_map,
    }

    generated_at = datetime.now(timezone.utc).isoformat()
    items: list[dict[str, object]] = []
    missing: list[dict[str, str]] = []

    for target in targets:
        partner = target["partner"]
        sku = target["sku"]
        source = maps[partner].get(sku)

        if source is None:
            missing.append({"partner": partner, "sku": sku})
            items.append(
                {
                    **target,
                    "found": False,
                    "available": False,
                    "quantity": 0,
                    "rrp": None,
                    "currency": "UAH",
                    "price_basis": "MISSING_FROM_LIVE_FEED",
                    "snapshot_at_utc": generated_at,
                }
            )
            continue

        rrp = positive_number(source.findtext("price"))
        available = source.get("available") == "true"
        quantity = quantity_for(source, partner, available)

        if partner == "ZAINSTRUMENTOM" and sku in za_adjusted:
            price_basis = "REGULAR_RRP_NORMALIZED_FROM_OLDPRICE"
        elif partner == "ZAINSTRUMENTOM":
            price_basis = "REGULAR_RRP_FROM_LIVE_FEED"
        elif partner == "SIGMA":
            price_basis = "CURRENT_RETAIL_FROM_LIVE_FEED"
        else:
            price_basis = "RETAIL_RRP_FROM_LIVE_FEED"

        items.append(
            {
                **target,
                "found": True,
                "available": available,
                "quantity": quantity,
                "rrp": round(rrp, 2) if rrp is not None else None,
                "currency": (source.findtext("currencyId") or "UAH").strip() or "UAH",
                "price_basis": price_basis,
                "snapshot_at_utc": generated_at,
            }
        )

    counts_by_partner = {
        partner: sum(1 for item in items if item["partner"] == partner)
        for partner in sorted(SUPPORTED_PARTNERS)
    }
    found_by_partner = {
        partner: sum(
            1
            for item in items
            if item["partner"] == partner and bool(item["found"])
        )
        for partner in sorted(SUPPORTED_PARTNERS)
    }

    payload: dict[str, object] = {
        "schema_version": 1,
        "source_master": "TALPA_KIT_MASTER_FINAL_v1_0",
        "generated_at_utc": generated_at,
        "configured_sku_count": len(targets),
        "found_count": sum(bool(item["found"]) for item in items),
        "missing_count": len(missing),
        "available_count": sum(bool(item["available"]) for item in items),
        "counts_by_partner": counts_by_partner,
        "found_by_partner": found_by_partner,
        "zainstrumentom_promotions_normalized": len(za_adjustments),
        "missing": missing,
        "items": items,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "KIT_PRICE_SNAPSHOT="
        + json.dumps(
            {
                "configured_sku_count": payload["configured_sku_count"],
                "found_count": payload["found_count"],
                "missing_count": payload["missing_count"],
                "available_count": payload["available_count"],
                "counts_by_partner": counts_by_partner,
                "found_by_partner": found_by_partner,
                "zainstrumentom_promotions_normalized": len(za_adjustments),
            },
            ensure_ascii=False,
        )
    )
    return payload
