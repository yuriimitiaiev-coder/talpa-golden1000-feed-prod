#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pool_common import GRAND_URL, download, supplier_offer_map

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "diagnostics"
JSON_OUT = OUT_DIR / "grand_drill_candidates.json"
CSV_OUT = OUT_DIR / "grand_drill_candidates.csv"

EXACT_SKUS = {"4933492820", "4933492826"}
DRILL_TERMS = (
    "дриль", "дрель", "шурупокрут", "шуруповерт", "percussion drill",
    "hammer drill", "drill driver", "combi drill",
)
IMPACT_TERMS = ("удар", "percussion", "hammer", "impact")
POWER_TERMS = ("18в", "18 в", "18v", "20в", "20 в", "20v", "m18")
SUPPORT_TERMS = (
    "акумулятор", "аккумулятор", "battery", "заряд", "charger",
    "зарядний", "зарядное",
)


def text(offer, tag: str) -> str:
    return (offer.findtext(tag) or "").strip()


def flatten_params(offer) -> str:
    parts = []
    for p in offer.findall("param"):
        name = (p.get("name") or "").strip()
        value = (p.text or "").strip()
        if name or value:
            parts.append(f"{name}: {value}" if name else value)
    return " | ".join(parts)


def offer_record(sku: str, offer) -> dict:
    name = text(offer, "name") or text(offer, "name_ua") or text(offer, "name_ru")
    vendor = text(offer, "vendor")
    description = text(offer, "description") or text(offer, "description_ua") or text(offer, "description_ru")
    params = flatten_params(offer)
    all_text = " ".join(str(x).strip() for x in offer.itertext() if str(x).strip())
    hay = " ".join([sku, name, vendor, description, params, all_text]).lower()

    qty_raw = text(offer, "quantity_in_stock")
    try:
        quantity = int(float(qty_raw.replace(",", "."))) if qty_raw else 0
    except Exception:
        quantity = 0
    price_raw = text(offer, "price")
    try:
        price = float(price_raw.replace(",", ".")) if price_raw else None
    except Exception:
        price = None

    is_milwaukee = "milwaukee" in hay
    is_4933 = sku.startswith("4933")
    is_drill = any(t in hay for t in DRILL_TERMS)
    is_18_20v = any(t in hay for t in POWER_TERMS)
    is_support = any(t in hay for t in SUPPORT_TERMS)
    mentions_impact = any(t in hay for t in IMPACT_TERMS)

    if sku in EXACT_SKUS:
        category = "EXACT_TARGET"
    elif is_milwaukee:
        category = "MILWAUKEE_ANY"
    elif is_4933:
        category = "SKU_4933_FAMILY"
    elif is_drill and is_18_20v:
        category = "DRILL_DRIVER_18_20V"
    elif is_support and is_18_20v:
        category = "POWER_SUPPORT_18_20V"
    else:
        category = "OTHER"

    return {
        "sku": sku,
        "name": name,
        "vendor": vendor,
        "price": price,
        "available": offer.get("available") == "true",
        "quantity": quantity,
        "url": text(offer, "url"),
        "category": category,
        "is_milwaukee": is_milwaukee,
        "is_4933_family": is_4933,
        "is_drill_driver": is_drill,
        "is_18_20v": is_18_20v,
        "mentions_impact": mentions_impact,
        "params": params,
    }


def main() -> None:
    data = download(GRAND_URL, "Grand Instrument")
    offer_map = supplier_offer_map(data, "Grand Instrument")

    all_rows = [offer_record(sku, offer) for sku, offer in offer_map.items()]
    rows = [r for r in all_rows if r["category"] != "OTHER"]
    rows.sort(key=lambda r: (
        0 if r["sku"] in EXACT_SKUS else 1,
        0 if r["is_milwaukee"] else 1,
        0 if r["mentions_impact"] else 1,
        0 if r["available"] else 1,
        (r["vendor"] or "").lower(),
        (r["name"] or "").lower(),
    ))

    vendor_counts = Counter((r["vendor"] or "(blank)") for r in all_rows)
    milwaukee_rows = [r for r in all_rows if r["is_milwaukee"]]
    family_4933_rows = [r for r in all_rows if r["is_4933_family"]]
    drill_rows = [r for r in all_rows if r["is_drill_driver"] and r["is_18_20v"]]
    impact_rows = [r for r in drill_rows if r["mentions_impact"]]
    available_impact_rows = [r for r in impact_rows if r["available"]]
    support_rows = [r for r in all_rows if r["category"] == "POWER_SUPPORT_18_20V"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "GRANDINSTRUMENT_FEED_URL",
        "total_feed_skus": len(offer_map),
        "exact_skus": {
            sku: next((r for r in all_rows if r["sku"] == sku), None)
            for sku in sorted(EXACT_SKUS)
        },
        "milwaukee_count": len(milwaukee_rows),
        "milwaukee_available_count": sum(1 for r in milwaukee_rows if r["available"]),
        "sku_4933_family_count": len(family_4933_rows),
        "drill_18_20v_count": len(drill_rows),
        "drill_18_20v_available_count": sum(1 for r in drill_rows if r["available"]),
        "impact_drill_candidate_count": len(impact_rows),
        "impact_drill_available_count": len(available_impact_rows),
        "power_support_18_20v_count": len(support_rows),
        "top_vendors": vendor_counts.most_common(25),
        "rows": rows,
    }
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fields = [
        "sku", "name", "vendor", "price", "available", "quantity", "url", "category",
        "is_milwaukee", "is_4933_family", "is_drill_driver", "is_18_20v", "mentions_impact", "params",
    ]
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        "total_feed_skus": payload["total_feed_skus"],
        "exact_skus": payload["exact_skus"],
        "milwaukee_count": payload["milwaukee_count"],
        "milwaukee_available_count": payload["milwaukee_available_count"],
        "sku_4933_family_count": payload["sku_4933_family_count"],
        "drill_18_20v_count": payload["drill_18_20v_count"],
        "drill_18_20v_available_count": payload["drill_18_20v_available_count"],
        "impact_drill_candidate_count": payload["impact_drill_candidate_count"],
        "impact_drill_available_count": payload["impact_drill_available_count"],
        "power_support_18_20v_count": payload["power_support_18_20v_count"],
        "milwaukee_rows": milwaukee_rows[:25],
        "available_impact_drills": available_impact_rows[:25],
        "available_drill_18_20v": [r for r in drill_rows if r["available"]][:25],
        "power_support_18_20v": support_rows[:25],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
