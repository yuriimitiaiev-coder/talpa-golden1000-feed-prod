#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile

from build_kit_price_snapshot import write_kit_price_snapshot
from content_patches import patch_grand_content, validate_grand_output
from price_guard import normalize_zainstrumentom_promotions
from pool_common import (
    GRAND_URL,
    GPL_URL,
    INDEX_HTML,
    MAX_CAPACITY,
    OUTPUT_DIR,
    OUTPUT_XML,
    PUBLISHED_FEED_URL,
    SIGMA_URL,
    STATUS_JSON,
    TEKNOSEL_URL,
    ZA_URL,
    download,
    feed_offer_map,
    google_merchant_offer_map,
    gpl_offer_map,
    load_groups,
    load_pool,
    supplier_offer_map,
)
from pool_builder import build_xml


def write_atomically(path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(data)
        temp_name = handle.name
    os.replace(temp_name, path)


def _offer_text(offer) -> str:
    return " ".join(
        (offer.findtext(tag) or "").strip()
        for tag in ("name_ua", "name", "vendor", "vendorCode")
    ).lower()


def _print_live_probe(source_maps: dict[str, dict], active_skus: set[str]) -> None:
    probes = {
        "DRILLS_ANY": lambda text: "сверд" in text or "сверл" in text or "drill" in text,
        "METAL_DRILLS": lambda text: ("сверд" in text or "сверл" in text or "drill" in text) and ("метал" in text or "metal" in text or "hss" in text),
        "SPADE_DRILLS": lambda text: "перов" in text or "spade" in text or "лопат" in text,
        "PAINT_TRAYS": lambda text: "кювет" in text or "лоток" in text,
    }
    for label, predicate in probes.items():
        print(f"LIVE_PROBE_{label}_BEGIN")
        found = 0
        limit = 100 if label == "DRILLS_ANY" else 40
        for supplier in ("SIGMA", "ZAINSTRUMENTOM", "GRANDINSTRUMENT", "TEKNOSEL"):
            for sku, offer in source_maps[supplier].items():
                if offer.get("available") != "true" or sku in active_skus:
                    continue
                text = _offer_text(offer)
                if not predicate(text):
                    continue
                name = (offer.findtext("name_ua") or offer.findtext("name") or "").strip().replace("\n", " ")
                price = (offer.findtext("price") or "").strip()
                category = (offer.findtext("categoryId") or "").strip()
                print(f"LIVE_PROBE|{label}|{supplier}|{sku}|{price}|cat={category}|{name}")
                found += 1
                if found >= limit:
                    break
            if found >= limit:
                break
        print(f"LIVE_PROBE_{label}_END count={found}")

    explicit = {
        "SIGMA": ["1193081", "1193071", "1191692", "1191682", "5035865", "2723025", "1314055"],
        "ZAINSTRUMENTOM": ["20082", "20014", "20011", "20076", "20077", "20125", "20146", "RM 418 1800"],
    }
    for supplier, skus in explicit.items():
        for sku in skus:
            offer = source_maps[supplier].get(sku)
            if offer is None:
                print(f"LIVE_EXACT|{supplier}|{sku}|MISSING")
                continue
            name = (offer.findtext("name_ua") or offer.findtext("name") or "").strip().replace("\n", " ")
            price = (offer.findtext("price") or "").strip()
            category = (offer.findtext("categoryId") or "").strip()
            print(f"LIVE_EXACT|{supplier}|{sku}|available={offer.get('available')}|price={price}|cat={category}|{name}")


def main() -> None:
    pool = load_pool()
    groups = load_groups()
    active_rows = [r for r in pool if r["status"] == "ACTIVE"]
    reserve_rows = [r for r in pool if r["status"] == "RESERVE"]

    published_data = download(PUBLISHED_FEED_URL, "published feed", optional=True)
    published_map = feed_offer_map(published_data, "published feed") if published_data else {}
    sigma_map = supplier_offer_map(download(SIGMA_URL, "SIGMA"), "SIGMA")
    za_map = supplier_offer_map(download(ZA_URL, "Zainstrumentom"), "Zainstrumentom")
    za_promo_adjustments = normalize_zainstrumentom_promotions(za_map)
    teknosel_map = google_merchant_offer_map(download(TEKNOSEL_URL, "TEKNOSEL"), "TEKNOSEL")
    grand_map = supplier_offer_map(download(GRAND_URL, "Grand Instrument"), "Grand Instrument")
    gpl_map = gpl_offer_map(download(GPL_URL, "GPL"), "GPL")

    source_maps = {
        "SIGMA": sigma_map,
        "ZAINSTRUMENTOM": za_map,
        "TEKNOSEL": teknosel_map,
        "GRANDINSTRUMENT": grand_map,
        "GPL": gpl_map,
    }
    unresolved = [
        r["sku"]
        for r in active_rows
        if source_maps[r["supplier"]].get(r["sku"]) is None
        and not r["prom_offer_id"]
        and r["sku"] not in published_map
    ]
    if unresolved:
        print("UNRESOLVED_ACTIVE_NO_FALLBACK=" + ",".join(unresolved))
        _print_live_probe(source_maps, {r["sku"] for r in active_rows})

    # TALPA only patches verified supplier-content defects. Price guarding for
    # ZaInstrumentom is handled separately above and affects commercial fields only.
    patch_grand_content(published_map)
    patch_grand_content(grand_map)

    xml_bytes, metadata = build_xml(
        active_rows,
        groups,
        published_map,
        sigma_map,
        za_map,
        teknosel_map,
        grand_map,
        gpl_map,
    )
    validate_grand_output(xml_bytes)

    metadata.update(
        {
            "pool_configured": len(pool),
            "reserve_configured": len(reserve_rows),
            "free_slots": MAX_CAPACITY - len(pool),
            "active_headroom": MAX_CAPACITY - len(active_rows),
            "zainstrumentom_promotions_guarded": len(za_promo_adjustments),
            "zainstrumentom_promotion_adjustments": za_promo_adjustments,
        }
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_atomically(OUTPUT_XML, xml_bytes)
    STATUS_JSON.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Stage 3 B2B: build a compact RRP/availability snapshot for the 99 unique
    # SKU used by frozen TALPA KIT-01…06. This reuses the same already-downloaded
    # supplier maps; it does not change Golden1000 commercial logic.
    write_kit_price_snapshot(
        sigma_map=sigma_map,
        za_map=za_map,
        grand_map=grand_map,
        za_adjustments=za_promo_adjustments,
    )

    INDEX_HTML.write_text(
        f"""<!doctype html>
<html lang="uk">
<head><meta charset="utf-8"><title>TALPA Golden1000 Feed</title></head>
<body>
<h1>TALPA Golden1000 — controlled pool</h1>
<p>Максимальна місткість: {metadata['capacity']} SKU</p>
<p>Активних: {metadata['active']}</p>
<p>RESERVE у файлі: {metadata['reserve_configured']}</p>
<p>Вільних місць у пулі: {metadata['free_slots']}</p>
<p>SKU без актуального запису постачальника: {metadata['supplier_missing_count']}</p>
<p>Акцій ZaInstrumentom захищено: {metadata['zainstrumentom_promotions_guarded']}</p>
<p>Оновлено UTC: {metadata['generated_at_utc']}</p>
<p><a href="golden1000.xml">golden1000.xml</a></p>
<p><a href="status.json">status.json</a></p>
<p><a href="kit_price_snapshot.json">kit_price_snapshot.json</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
