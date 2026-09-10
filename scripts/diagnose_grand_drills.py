#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
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
IMPACT_TERMS = ("ударн", "percussion", "hammer")
POWER_TERMS = ("18в", "18 в", "18v", "20в", "20 в", "20v", "m18")
SUPPORT_TERMS = (
    "акумулятор", "аккумулятор", "battery", "заряд", "charger", "m18",
)


def text(offer, tag: str) -> str:
    return (offer.findtext(tag) or "").strip()


def offer_record(sku: str, offer) -> dict:
    name = text(offer, "name") or text(offer, "name_ua") or text(offer, "name_ru")
    vendor = text(offer, "vendor")
    description = text(offer, "description") or text(offer, "description_ua") or text(offer, "description_ru")
    hay = " ".join([sku, name, vendor, description]).lower()
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

    category = "OTHER"
    if sku in EXACT_SKUS:
        category = "EXACT_TARGET"
    elif any(t in hay for t in DRILL_TERMS):
        category = "DRILL_DRIVER"
    elif "milwaukee" in hay and any(t in hay for t in SUPPORT_TERMS):
        category = "MILWAUKEE_SUPPORT"

    return {
        "sku": sku,
        "name": name,
        "vendor": vendor,
        "price": price,
        "available": offer.get("available") == "true",
        "quantity": quantity,
        "url": text(offer, "url"),
        "category": category,
        "is_18_20v": any(t in hay for t in POWER_TERMS),
        "mentions_impact": any(t in hay for t in IMPACT_TERMS),
    }


def main() -> None:
    data = download(GRAND_URL, "Grand Instrument")
    offer_map = supplier_offer_map(data, "Grand Instrument")

    rows = []
    for sku, offer in offer_map.items():
        r = offer_record(sku, offer)
        keep = False
        if r["category"] == "EXACT_TARGET":
            keep = True
        elif r["category"] == "DRILL_DRIVER" and r["is_18_20v"]:
            keep = True
        elif r["category"] == "MILWAUKEE_SUPPORT":
            keep = True
        if keep:
            rows.append(r)

    rows.sort(key=lambda r: (
        0 if r["category"] == "EXACT_TARGET" else 1,
        0 if r["mentions_impact"] else 1,
        0 if r["available"] else 1,
        (r["vendor"] or "").lower(),
        (r["name"] or "").lower(),
    ))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "GRANDINSTRUMENT_FEED_URL",
        "total_feed_skus": len(offer_map),
        "exact_skus": {
            sku: next((r for r in rows if r["sku"] == sku), None)
            for sku in sorted(EXACT_SKUS)
        },
        "candidate_count": len(rows),
        "available_candidate_count": sum(1 for r in rows if r["available"]),
        "impact_candidate_count": sum(1 for r in rows if r["mentions_impact"]),
        "rows": rows,
    }
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fields = ["sku", "name", "vendor", "price", "available", "quantity", "url", "category", "is_18_20v", "mentions_impact"]
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        "total_feed_skus": payload["total_feed_skus"],
        "candidate_count": payload["candidate_count"],
        "available_candidate_count": payload["available_candidate_count"],
        "impact_candidate_count": payload["impact_candidate_count"],
        "exact_skus": payload["exact_skus"],
        "top_available": [r for r in rows if r["available"]][:20],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
