#!/usr/bin/env python3
"""Build a resilient TALPA Golden 1000 XML feed.

Fresh products are taken from the current supplier feed. If a Golden code
has disappeared from the current supplier feed, the last known product card
from docs/golden1000.xml is retained but forced to available="false".

This keeps the output at exactly 1000 products while preventing obsolete
products from remaining available for sale.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
CODES_FILE = ROOT / "golden_codes.txt"
OUTPUT_DIR = ROOT / "docs"
OUTPUT_XML = OUTPUT_DIR / "golden1000.xml"
STATUS_JSON = OUTPUT_DIR / "status.json"
INDEX_HTML = OUTPUT_DIR / "index.html"

SOURCE_URL = os.environ.get("SOURCE_FEED_URL", "").strip()
EXPECTED_COUNT = int(os.environ.get("EXPECTED_COUNT", "1000"))
TIMEOUT_SECONDS = int(os.environ.get("DOWNLOAD_TIMEOUT_SECONDS", "120"))
MAX_FALLBACK_MISSING = int(os.environ.get("MAX_FALLBACK_MISSING", "50"))


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def xml_parser() -> etree.XMLParser:
    return etree.XMLParser(
        strip_cdata=False,
        remove_blank_text=False,
        recover=False,
        resolve_entities=False,
        no_network=True,
        huge_tree=True,
    )


def load_codes() -> set[str]:
    if not CODES_FILE.exists():
        fail(f"Missing {CODES_FILE}")

    codes = {
        line.strip()
        for line in CODES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if len(codes) != EXPECTED_COUNT:
        fail(f"Expected {EXPECTED_COUNT} unique codes, got {len(codes)}")
    return codes


def download_feed(url: str) -> bytes:
    if not url:
        fail("SOURCE_FEED_URL is empty")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TALPA-Golden1000-Filter/2.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = response.read()
    except Exception as exc:
        fail(f"Cannot download source feed: {exc}")

    if len(data) < 1000:
        fail(f"Downloaded feed is unexpectedly small: {len(data)} bytes")
    return data


def parse_xml(data: bytes, label: str) -> etree._Element:
    try:
        return etree.fromstring(data, xml_parser())
    except Exception as exc:
        fail(f"Invalid {label} XML: {exc}")


def get_shop_parts(root: etree._Element, label: str):
    shop = root.find("shop")
    if shop is None:
        fail(f"{label} XML has no <shop> element")
    categories = shop.find("categories")
    offers = shop.find("offers")
    if categories is None or offers is None:
        fail(f"{label} XML has no <categories> or <offers> element")
    return shop, categories, offers


def offer_map(offers: etree._Element, label: str) -> dict[str, etree._Element]:
    result: dict[str, etree._Element] = {}
    duplicates: set[str] = set()
    for offer in offers.findall("offer"):
        code = (offer.findtext("vendorCode") or "").strip()
        if not code:
            continue
        if code in result:
            duplicates.add(code)
        else:
            result[code] = offer
    if duplicates:
        fail(f"Duplicate vendorCode values in {label}: {sorted(duplicates)[:20]}")
    return result


def category_map(categories: etree._Element) -> dict[str, etree._Element]:
    return {
        category.get("id"): category
        for category in categories.findall("category")
        if category.get("id")
    }


def force_unavailable(offer: etree._Element) -> etree._Element:
    result = copy.deepcopy(offer)

    # YML availability flag used by Prom.ua.
    result.set("available", "false")

    # Remove/disable any "ready to ship" marker that could conflict.
    result.attrib.pop("in_stock", None)
    for node in result.findall("in_stock"):
        node.getparent().remove(node)

    # IMPORTANT: Prom may keep the previous stock quantity when the tag is
    # absent. A positive retained quantity can switch the item back to
    # "В наявності", even when available="false". Therefore quantity_in_stock
    # must always be present and explicitly equal to zero.
    quantity_node = result.find("quantity_in_stock")
    if quantity_node is None:
        quantity_node = etree.Element("quantity_in_stock")
        quantity_node.text = "0"

        # Keep a predictable YML order: add after currencyId when possible.
        currency_node = result.find("currencyId")
        if currency_node is not None:
            result.insert(result.index(currency_node) + 1, quantity_node)
        else:
            result.insert(0, quantity_node)
    else:
        quantity_node.text = "0"

    # Zero any alternative quantity-like fields if they exist.
    for tag in ("quantity", "stock_quantity", "amount"):
        node = result.find(tag)
        if node is not None:
            node.text = "0"

    return result


def build_filtered_feed(source: bytes, wanted_codes: set[str]) -> tuple[bytes, dict]:
    source_root = parse_xml(source, "source")
    _, source_categories, source_offers = get_shop_parts(source_root, "Source")

    if not OUTPUT_XML.exists():
        fail(
            "Fallback file docs/golden1000.xml is missing. "
            "Upload the initial Golden 1000 XML to the repository."
        )
    previous_root = parse_xml(OUTPUT_XML.read_bytes(), "fallback")
    _, previous_categories, previous_offers = get_shop_parts(previous_root, "Fallback")

    current_offer_by_code = offer_map(source_offers, "source feed")
    previous_offer_by_code = offer_map(previous_offers, "fallback feed")

    missing_codes = sorted(wanted_codes - current_offer_by_code.keys())
    if len(missing_codes) > MAX_FALLBACK_MISSING:
        fail(
            f"Current feed is missing {len(missing_codes)} Golden codes, "
            f"which exceeds safety limit {MAX_FALLBACK_MISSING}. "
            f"First missing codes: {missing_codes[:20]}"
        )

    unavailable_without_fallback = [
        code for code in missing_codes if code not in previous_offer_by_code
    ]
    if unavailable_without_fallback:
        fail(
            "Missing Golden codes have no fallback product card: "
            f"{unavailable_without_fallback[:20]}"
        )

    # Keep the source document structure, but rebuild categories and offers.
    output_root = copy.deepcopy(source_root)
    _, output_categories, output_offers = get_shop_parts(output_root, "Output")
    output_categories.clear()
    output_offers.clear()

    selected_offers: list[etree._Element] = []
    fresh_count = 0
    fallback_count = 0
    used_category_ids: set[str] = set()

    # Stable ordering: current source order first, then fallback-only products.
    added_codes: set[str] = set()
    for source_offer in source_offers.findall("offer"):
        code = (source_offer.findtext("vendorCode") or "").strip()
        if code in wanted_codes and code not in added_codes:
            selected = copy.deepcopy(source_offer)
            selected_offers.append(selected)
            added_codes.add(code)
            fresh_count += 1
            category_id = (selected.findtext("categoryId") or "").strip()
            if category_id:
                used_category_ids.add(category_id)

    for code in missing_codes:
        selected = force_unavailable(previous_offer_by_code[code])
        selected_offers.append(selected)
        added_codes.add(code)
        fallback_count += 1
        category_id = (selected.findtext("categoryId") or "").strip()
        if category_id:
            used_category_ids.add(category_id)

    if added_codes != wanted_codes:
        unresolved = sorted(wanted_codes - added_codes)
        fail(f"Could not assemble all Golden codes: {unresolved[:20]}")

    # Build a unified category map: current feed first, fallback feed second.
    source_category_by_id = category_map(source_categories)
    previous_category_by_id = category_map(previous_categories)
    unified_category_by_id = dict(previous_category_by_id)
    unified_category_by_id.update(source_category_by_id)

    parent_by_id = {
        category_id: category.get("parentId")
        for category_id, category in unified_category_by_id.items()
    }

    categories_to_keep = set(used_category_ids)
    for category_id in list(used_category_ids):
        parent_id = parent_by_id.get(category_id)
        visited: set[str] = set()
        while parent_id and parent_id not in visited:
            visited.add(parent_id)
            categories_to_keep.add(parent_id)
            parent_id = parent_by_id.get(parent_id)

    appended_categories: set[str] = set()
    for category in source_categories.findall("category"):
        category_id = category.get("id")
        if category_id in categories_to_keep:
            output_categories.append(copy.deepcopy(category))
            appended_categories.add(category_id)

    for category in previous_categories.findall("category"):
        category_id = category.get("id")
        if category_id in categories_to_keep and category_id not in appended_categories:
            output_categories.append(copy.deepcopy(category))
            appended_categories.add(category_id)

    missing_category_defs = sorted(categories_to_keep - appended_categories)
    if missing_category_defs:
        fail(f"Missing category definitions: {missing_category_defs[:20]}")

    for offer in selected_offers:
        output_offers.append(offer)

    xml_bytes = etree.tostring(
        output_root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )

    # Independent final validation.
    check_root = parse_xml(xml_bytes, "generated")
    _, _, check_offers = get_shop_parts(check_root, "Generated")
    check_codes = [
        (offer.findtext("vendorCode") or "").strip()
        for offer in check_offers.findall("offer")
    ]
    if len(check_codes) != EXPECTED_COUNT:
        fail(f"Generated feed has {len(check_codes)} offers, expected {EXPECTED_COUNT}")
    if len(set(check_codes)) != EXPECTED_COUNT:
        fail("Generated feed contains duplicate vendorCode values")
    if set(check_codes) != wanted_codes:
        fail("Generated feed codes do not match Golden code list")

    fallback_offers = [
        offer
        for offer in check_offers.findall("offer")
        if (offer.findtext("vendorCode") or "").strip() in missing_codes
    ]
    if any(offer.get("available") != "false" for offer in fallback_offers):
        fail("At least one fallback product was not marked unavailable")

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "offers": len(check_codes),
        "fresh_offers": fresh_count,
        "fallback_unavailable": fallback_count,
        "missing_codes": missing_codes,
        "categories": len(output_categories.findall("category")),
        "source_bytes": len(source),
        "output_bytes": len(xml_bytes),
        "sha256": hashlib.sha256(xml_bytes).hexdigest(),
    }
    return xml_bytes, metadata


def write_atomically(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(data)
        temp_name = handle.name
    os.replace(temp_name, path)


def main() -> None:
    wanted_codes = load_codes()
    source = download_feed(SOURCE_URL)
    xml_bytes, metadata = build_filtered_feed(source, wanted_codes)

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
<p>Актуальних із джерела: {metadata['fresh_offers']}</p>
<p>Відсутніх у постачальника та вимкнених: {metadata['fallback_unavailable']}</p>
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
