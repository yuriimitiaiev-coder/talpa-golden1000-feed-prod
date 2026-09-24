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

    exact_results = {}
    for primary, candidates in EXACT.items():
        rows = []
        for partner, sku, rationale in candidates:
            rows.append(item(partner, sku, maps[partner].get(sku), rationale, "EXACT_CANDIDATE"))
        exact_results[primary] = rows

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

    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "feed-backed candidate discovery for blocked MASTER v1.0 functions",
        "exact_candidates": exact_results,
        "keyword_available_matches": keyword_results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
