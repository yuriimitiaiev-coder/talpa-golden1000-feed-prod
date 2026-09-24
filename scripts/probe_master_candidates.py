#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pool_common import (
    GRAND_URL, GPL_URL, SIGMA_URL, TEKNOSEL_URL, ZA_URL,
    download, google_merchant_offer_map, gpl_offer_map, supplier_offer_map,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "master_candidate_probe.json"

EXACT = {
    "1193101": [
        ("SIGMA", "1191712", "19-piece metal drill set 1-10 mm"),
    ],
    "1303311": [
        ("SIGMA", "1314665", "spade drill set 10/12/16/18/20/25 mm"),
    ],
    "1719691": [
        ("SIGMA", "1715051", "concrete drill 4 mm"),
        ("SIGMA", "1718071", "concrete drill 5 mm"),
        ("SIGMA", "1718111", "concrete drill 6 mm"),
        ("SIGMA", "1718371", "concrete drill 8 mm candidate"),
        ("SIGMA", "1718611", "concrete drill 10 mm"),
    ],
    "1602-2755": [
        ("SIGMA", "1811121", "SDS-plus 8x160 mm"),
    ],
}

BLOCKED_PRIMARY = [
    "1193101", "1303311", "1719691", "1109-0872", "1602-2755",
    "YT-82055", "YT-827722", "YT-82786", "YT-828461",
]

SCORING = {
    "1109-0872": [
        (4, ["кром", "edge"]), (4, ["гіпс", "гипс", "drywall"]), (3, ["рубан", "plane"]),
        (5, ["45"]), (2, ["фаск", "bevel"]),
    ],
    "1193101": [
        (4, ["сверд", "сверл", "drill"]), (4, ["метал", "metal"]), (3, ["набір", "набор", "set"]),
        (2, ["1–10", "1-10", "1.0-10.0", "1,0-10,0"]), (1, ["hss"]),
    ],
    "1303311": [
        (5, ["перов", "spade"]), (4, ["сверд", "сверл", "drill"]), (3, ["дерев", "wood"]),
        (3, ["набір", "набор", "set"]),
    ],
    "1719691": [
        (4, ["сверд", "сверл", "drill"]), (4, ["бетон", "concrete"]), (3, ["набір", "набор", "set"]),
        (2, ["4", "5", "6", "8", "10"]),
    ],
    "1602-2755": [
        (5, ["sds-plus", "sds+"]), (4, ["бур"]), (4, ["бетон", "concrete"]),
        (4, ["8x160", "8×160", "8х160"]),
    ],
    "YT-82055": [
        (5, ["дриль", "дрель", "drill"]), (5, ["міксер", "миксер", "mixer"]),
        (3, ["1200"]), (2, ["патрон", "chuck"]),
    ],
    "YT-827722": [
        (6, ["перфоратор", "rotary hammer"]), (5, ["акум", "аккум", "cordless"]),
        (4, ["sds-plus", "sds+"]), (3, ["18"]), (2, ["2.5", "2,5"]),
    ],
    "YT-82786": [
        (5, ["шуруп", "driver"]), (4, ["дриль", "дрель", "drill"]), (4, ["удар", "impact"]),
        (4, ["акум", "аккум", "cordless"]), (3, ["18"]), (2, ["40"]),
    ],
    "YT-828461": [
        (6, ["акум", "аккум", "battery"]), (4, ["18"]), (3, ["2ah", "2 ah", "2а·год", "2 а"]),
        (2, ["li-ion", "літій", "литий"]),
    ],
}

KEYWORDS = {
    "1109-0872": ["45", "гіпсокарт", "кром", "рубан"],
    "YT-82055": ["дриль", "міксер"],
    "YT-827722": ["перфоратор", "акумулятор", "sds"],
    "YT-82786": ["дриль", "шуруп", "удар", "18"],
    "YT-828461": ["акумулятор", "18", "2"],
}

def text_of(el) -> str:
    fields = [
        el.findtext("name_ua"), el.findtext("name"), el.findtext("title"),
        el.findtext("description"), el.findtext("vendor"), el.findtext("url"),
    ]
    return " ".join((x or "").strip() for x in fields if x).lower()

def item(partner: str, sku: str, el, rationale: str, matched_by: str) -> dict:
    if el is None:
        return {
            "partner": partner, "sku": sku, "found": False, "available": False,
            "quantity": 0, "price": None, "name": "", "url": "",
            "rationale": rationale, "matched_by": matched_by,
        }
    available = el.get("available") == "true"
    qty_raw = (el.findtext("quantity_in_stock") or "").strip()
    try:
        qty = max(int(float(qty_raw.replace(",", "."))), 0) if qty_raw else (1 if available else 0)
    except ValueError:
        qty = 1 if available else 0
    price_raw = (el.findtext("price") or "").strip().replace(",", ".")
    try:
        price = float(price_raw) if price_raw else None
    except ValueError:
        price = None
    name = (el.findtext("name_ua") or el.findtext("name") or el.findtext("title") or "").strip()
    return {
        "partner": partner, "sku": sku, "found": True, "available": available,
        "quantity": qty, "price": price, "name": name,
        "url": (el.findtext("url") or "").strip(),
        "rationale": rationale, "matched_by": matched_by,
    }

def main() -> None:
    maps = {
        "SIGMA": supplier_offer_map(download(SIGMA_URL, "SIGMA"), "SIGMA"),
        "ZAINSTRUMENTOM": supplier_offer_map(download(ZA_URL, "Zainstrumentom"), "Zainstrumentom"),
        "GRANDINSTRUMENT": supplier_offer_map(download(GRAND_URL, "Grand Instrument"), "Grand Instrument"),
        "TEKNOSEL": google_merchant_offer_map(download(TEKNOSEL_URL, "TEKNOSEL"), "TEKNOSEL"),
        "GPL": gpl_offer_map(download(GPL_URL, "GPL"), "GPL"),
    }

    same_sku_sources = {}
    for primary in BLOCKED_PRIMARY:
        rows = []
        for partner, mp in maps.items():
            rows.append(item(partner, primary, mp.get(primary), "same PRIMARY SKU in another connected feed", "A2_SAME_SKU"))
        same_sku_sources[primary] = rows

    exact_results = {}
    for primary, candidates in EXACT.items():
        rows = []
        for partner, sku, rationale in candidates:
            rows.append(item(partner, sku, maps[partner].get(sku), rationale, "EXACT_CANDIDATE"))
        exact_results[primary] = rows

    scored_results = {}
    for primary, profile in SCORING.items():
        matches = []
        for partner, mp in maps.items():
            for sku, el in mp.items():
                hay = text_of(el)
                score = 0
                matched = []
                for weight, variants in profile:
                    if any(v.lower() in hay for v in variants):
                        score += weight
                        matched.append("/".join(variants))
                if score <= 0:
                    continue
                rec = item(partner, sku, el, f"score={score}; " + "; ".join(matched), "FUNCTION_SCORE")
                if rec["available"]:
                    rec["score"] = score
                    matches.append(rec)
        matches.sort(key=lambda x: (-x["score"], x["partner"], x["sku"]))
        scored_results[primary] = matches[:30]

    keyword_results = {}
    for primary, words in KEYWORDS.items():
        matches = []
        for partner, mp in maps.items():
            for sku, el in mp.items():
                hay = text_of(el)
                if all(w.lower() in hay for w in words):
                    rec = item(partner, sku, el, " + ".join(words), "KEYWORDS_ALL")
                    if rec["available"]:
                        matches.append(rec)
        matches.sort(key=lambda x: (x["partner"], x["sku"]))
        keyword_results[primary] = matches[:40]

    inventory_specs = {
        "drills_and_drivers": ["дрил", "дрель", "шуруп"],
        "rotary_hammers": ["перфоратор"],
        "18v_batteries": ["акумулятор", "аккумулятор", "battery"],
        "mixers": ["міксер", "миксер", "mixer"],
        "drill_bits": ["сверд", "сверл", "бур"],
        "drywall_edge": ["гіпс", "гипс", "drywall", "кром"],
    }
    keyword_inventory = {}
    for label, needles in inventory_specs.items():
        rows = []
        for partner, mp in maps.items():
            for sku, el in mp.items():
                rec = item(partner, sku, el, label, "CATALOG_INVENTORY")
                if not rec["available"]:
                    continue
                name = rec["name"].lower()
                if any(n in name for n in needles):
                    rows.append(rec)
        rows.sort(key=lambda x: (x["partner"], x["sku"]))
        keyword_inventory[label] = rows[:250]

    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "feed-backed candidate discovery for blocked MASTER v1.0 functions",
        "same_sku_sources": same_sku_sources,
        "exact_candidates": exact_results,
        "scored_available_matches": scored_results,
        "available_catalog_inventory": keyword_inventory,
        "keyword_available_matches": keyword_results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
