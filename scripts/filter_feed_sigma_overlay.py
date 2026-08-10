#!/usr/bin/env python3
"""Build TALPA Golden1000 with a safe commercial overlay from SIGMA.

For existing TALPA cards assigned to SIGMA, the Dropshipping.ua product card
remains the structural template (offer id, vendorCode, category, content).
Only commercial fields are overlaid from the current SIGMA public XML:
price, availability and a conservative quantity marker.

This minimizes the risk that Prom.ua creates duplicate cards or overwrites
manually optimized content during the 424-card migration stage.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from lxml import etree

from filter_feed import (
    ROOT,
    OUTPUT_DIR,
    OUTPUT_XML,
    STATUS_JSON,
    INDEX_HTML,
    SOURCE_URL,
    ZAINSTRUMENTOM_URL,
    EXPECTED_COUNT,
    load_codes,
    load_supplier_map,
    download_feed,
    parse_xml,
    get_shop_parts,
    offer_map,
    remap_category_ids,
    build_filtered_feed,
    write_atomically,
)

SIGMA_URL = os.environ.get(
    "SIGMA_FEED_URL",
    "https://sigma.ua/bitrix/catalog_export/marketsigma_ua.php",
).strip()
SIGMA_SKU_MAP_FILE = ROOT / "sigma_sku_map.txt"


def load_sigma_sku_map() -> dict[str, str]:
    if not SIGMA_SKU_MAP_FILE.exists():
        return {}
    result: dict[str, str] = {}
    for raw in SIGMA_SKU_MAP_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SystemExit(f"Invalid sigma_sku_map line: {line!r}")
        talpa_code, sigma_code = [x.strip() for x in line.split("=", 1)]
        if not talpa_code or not sigma_code:
            raise SystemExit(f"Invalid sigma_sku_map line: {line!r}")
        if talpa_code in result:
            raise SystemExit(f"Duplicate TALPA code in sigma_sku_map: {talpa_code}")
        result[talpa_code] = sigma_code
    return result


def set_text(parent: etree._Element, tag: str, value: str) -> None:
    node = parent.find(tag)
    if node is None:
        node = etree.Element(tag)
        parent.append(node)
    node.text = value


def overlay_sigma_commercial_fields(
    talpa_offer: etree._Element,
    sigma_offer: etree._Element,
) -> etree._Element:
    """Keep TALPA identity/content, replace only commercial fields."""
    result = copy.deepcopy(talpa_offer)

    sigma_price = (sigma_offer.findtext("price") or "").strip()
    if not sigma_price:
        raise SystemExit("SIGMA offer has no price")
    set_text(result, "price", sigma_price)

    available = sigma_offer.get("available") == "true"
    result.set("available", "true" if available else "false")

    # Do not carry a stale crossed-out price from the former supplier.
    for oldprice in list(result.findall("oldprice")):
        result.remove(oldprice)

    # Prom can retain a previous stock quantity when a feed omits quantity.
    # For a binary SIGMA feed, publish 1 when available and 0 when unavailable.
    quantity = result.find("quantity_in_stock")
    if quantity is None:
        quantity = etree.Element("quantity_in_stock")
        currency = result.find("currencyId")
        if currency is not None:
            result.insert(result.index(currency) + 1, quantity)
        else:
            result.insert(0, quantity)
    quantity.text = "1" if available else "0"

    for tag in ("quantity", "stock_quantity", "amount"):
        node = result.find(tag)
        if node is not None:
            node.text = "1" if available else "0"

    return result


def main() -> None:
    wanted_codes = load_codes()
    supplier_map = load_supplier_map()
    sigma_sku_map = load_sigma_sku_map()

    sigma_assigned = {c for c, s in supplier_map.items() if s == "SIGMA"}
    za_assigned = {c for c, s in supplier_map.items() if s == "ZAINSTRUMENTOM"}

    print(f"Golden codes: {len(wanted_codes)}")
    print(f"Supplier overrides: {len(supplier_map)}")
    print(f"SIGMA assigned: {len(sigma_assigned)}")
    print(f"Zainstrumentom assigned: {len(za_assigned)}")

    source = download_feed(SOURCE_URL, "Dropshipping.ua")
    source_root = parse_xml(source, "Dropshipping.ua")
    _, source_categories, source_offers = get_shop_parts(source_root, "Dropshipping.ua")

    sigma_missing: list[str] = []
    sigma_overlaid = 0

    if sigma_assigned:
        sigma_source = download_feed(SIGMA_URL, "SIGMA")
        sigma_root = parse_xml(sigma_source, "SIGMA")
        _, _, sigma_offers = get_shop_parts(sigma_root, "SIGMA")
        sigma_by_code = offer_map(sigma_offers, "SIGMA", strict_duplicates=False)

        for offer in list(source_offers.findall("offer")):
            code = (offer.findtext("vendorCode") or "").strip()
            if supplier_map.get(code) != "SIGMA":
                continue

            sigma_code = sigma_sku_map.get(code, code)
            sigma_offer = sigma_by_code.get(sigma_code)
            if sigma_offer is None:
                # Removing it causes the normal Golden1000 fallback mechanism
                # to keep the old card but force it unavailable.
                source_offers.remove(offer)
                sigma_missing.append(code)
                continue

            updated = overlay_sigma_commercial_fields(offer, sigma_offer)
            idx = source_offers.index(offer)
            source_offers.remove(offer)
            source_offers.insert(idx, updated)
            sigma_overlaid += 1

        # A SIGMA-assigned Golden code may already be absent from the current
        # Dropshipping feed. Mark it missing so fallback safety is visible.
        source_codes = {
            (o.findtext("vendorCode") or "").strip()
            for o in source_offers.findall("offer")
        }
        for code in sorted(sigma_assigned & wanted_codes):
            if code not in source_codes and code not in sigma_missing:
                sigma_missing.append(code)

    # Existing Zainstrumentom logic: remove explicitly assigned SKUs from
    # Dropshipping and replace them with the supplier's own product offers.
    zainstrumentom_source = (
        download_feed(ZAINSTRUMENTOM_URL, "Zainstrumentom")
        if ZAINSTRUMENTOM_URL and za_assigned
        else b""
    )

    if zainstrumentom_source:
        za_root = parse_xml(zainstrumentom_source, "Zainstrumentom")
        _, za_categories, za_offers = get_shop_parts(za_root, "Zainstrumentom")
        remap_category_ids(
            za_categories,
            za_offers,
            1_000_000_000,
            "Zainstrumentom",
        )
        za_by_code = offer_map(za_offers, "Zainstrumentom", strict_duplicates=False)

        for offer in list(source_offers.findall("offer")):
            code = (offer.findtext("vendorCode") or "").strip()
            if supplier_map.get(code) == "ZAINSTRUMENTOM":
                source_offers.remove(offer)

        for category in za_categories.findall("category"):
            source_categories.append(copy.deepcopy(category))

        for code in sorted(za_assigned):
            offer = za_by_code.get(code)
            if offer is not None:
                source_offers.append(copy.deepcopy(offer))

    merged_source = etree.tostring(
        source_root,
        encoding="utf-8",
        xml_declaration=True,
    )

    xml_bytes, metadata = build_filtered_feed(merged_source, wanted_codes)
    metadata.update(
        {
            "sigma_assigned": len(sigma_assigned & wanted_codes),
            "sigma_overlaid": sigma_overlaid,
            "sigma_missing": sorted(sigma_missing),
            "zainstrumentom_assigned": len(za_assigned & wanted_codes),
        }
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_atomically(OUTPUT_XML, xml_bytes)
    STATUS_JSON.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    INDEX_HTML.write_text(
        f"""<!doctype html>
<html lang="uk">
<head><meta charset="utf-8"><title>TALPA Golden 1000 Feed</title></head>
<body>
<h1>TALPA Golden 1000 Feed</h1>
<p>Товарів: {metadata['offers']}</p>
<p>SIGMA призначено: {metadata['sigma_assigned']}</p>
<p>SIGMA оновлено: {metadata['sigma_overlaid']}</p>
<p>SIGMA fallback: {len(metadata['sigma_missing'])}</p>
<p>Оновлено UTC: {metadata['generated_at_utc']}</p>
<p><a href="golden1000.xml">golden1000.xml</a></p>
<p><a href="status.json">status.json</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )
    (OUTPUT_DIR / ".nojekyll").touch()

    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
