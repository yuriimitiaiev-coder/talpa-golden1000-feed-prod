#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import tempfile
from urllib.parse import urlparse

from lxml import etree

from build_kit_price_snapshot import write_kit_price_snapshot
from build_kit_supply_resolver import write_kit_supply_resolver
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
    fail,
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
from pool_builder import SIGMA_MEDIA_REPAIR_SKUS, build_xml


def write_atomically(path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(data)
        temp_name = handle.name
    os.replace(temp_name, path)


SIGMA_MEDIA_PUBLIC_BASE = "https://yuriimitiaiev-coder.github.io/talpa-golden1000-feed-prod/media/sigma"


def mirror_sigma_media(sigma_map, active_rows, published_map) -> dict[str, int]:
    """Mirror known/problematic SIGMA media into the Pages artifact and rewrite source URLs."""
    media_dir = OUTPUT_DIR / "media" / "sigma"
    if media_dir.exists():
        shutil.rmtree(media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)

    selected: set[str] = set(SIGMA_MEDIA_REPAIR_SKUS)
    for row in active_rows:
        if row["supplier"] != "SIGMA":
            continue
        sku = row["sku"]
        if not row["prom_offer_id"] and sku not in published_map:
            selected.add(sku)

    mirrored_skus = 0
    mirrored_files = 0
    for sku in sorted(selected):
        source = sigma_map.get(sku)
        if source is None:
            fail(f"SIGMA media mirror source is missing for {sku}")
        pictures = [p for p in source.findall("picture") if (p.text or "").strip()][:10]
        if not pictures:
            fail(f"SIGMA media mirror has no source pictures for {sku}")

        hosted_urls: list[str] = []
        for index, picture in enumerate(pictures, start=1):
            source_url = (picture.text or "").strip()
            suffix = Path(urlparse(source_url).path).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
                suffix = ".jpg"
            data = download(source_url, f"SIGMA image {sku} #{index}")
            filename = f"{sku}_{index}{suffix}"
            target = media_dir / filename
            write_atomically(target, data)
            if target.stat().st_size < 500:
                fail(f"SIGMA mirrored image is unexpectedly small for {sku} #{index}")
            hosted_urls.append(f"{SIGMA_MEDIA_PUBLIC_BASE}/{filename}")
            mirrored_files += 1

        for node in list(source.findall("picture")):
            source.remove(node)
        for hosted_url in hosted_urls:
            etree.SubElement(source, "picture").text = hosted_url
        mirrored_skus += 1

    return {"sigma_media_mirrored_skus": mirrored_skus, "sigma_media_mirrored_files": mirrored_files}


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

    sigma_media_mirror = mirror_sigma_media(sigma_map, active_rows, published_map)

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
            **sigma_media_mirror,
        }
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_atomically(OUTPUT_XML, xml_bytes)
    STATUS_JSON.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Stage 3 B2B: compact live RRP/availability snapshot for the frozen 99 SKU.
    # This remains the direct PRIMARY SKU price source used by the existing Feed CO Engine.
    write_kit_price_snapshot(
        sigma_map=sigma_map,
        za_map=za_map,
        grand_map=grand_map,
        za_adjustments=za_promo_adjustments,
    )

    # Stage 5 B2B: resolve temporarily unavailable frozen MASTER SKU through the
    # explicitly approved live-coverage registry. MASTER itself is never rewritten.
    # The artifact is advisory/machine-readable and does not alter golden1000.xml.
    write_kit_supply_resolver(
        pool_rows=pool,
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
<p><a href="kit_supply_resolver.json">kit_supply_resolver.json</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
