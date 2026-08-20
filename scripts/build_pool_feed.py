#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile

from pool_common import (
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


def main() -> None:
    pool = load_pool()
    groups = load_groups()
    active_rows = [r for r in pool if r["status"] == "ACTIVE"]
    reserve_rows = [r for r in pool if r["status"] == "RESERVE"]

    published_data = download(PUBLISHED_FEED_URL, "published feed", optional=True)
    published_map = feed_offer_map(published_data, "published feed") if published_data else {}
    sigma_map = supplier_offer_map(download(SIGMA_URL, "SIGMA"), "SIGMA")
    za_map = supplier_offer_map(download(ZA_URL, "Zainstrumentom"), "Zainstrumentom")
    teknosel_map = google_merchant_offer_map(download(TEKNOSEL_URL, "TEKNOSEL"), "TEKNOSEL")

    xml_bytes, metadata = build_xml(
        active_rows,
        groups,
        published_map,
        sigma_map,
        za_map,
        teknosel_map,
    )
    metadata.update(
        {
            "pool_configured": len(pool),
            "reserve_configured": len(reserve_rows),
            "free_slots": MAX_CAPACITY - len(pool),
            "active_headroom": MAX_CAPACITY - len(active_rows),
        }
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_atomically(OUTPUT_XML, xml_bytes)
    STATUS_JSON.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
<p>Оновлено UTC: {metadata['generated_at_utc']}</p>
<p><a href="golden1000.xml">golden1000.xml</a></p>
<p><a href="status.json">status.json</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
