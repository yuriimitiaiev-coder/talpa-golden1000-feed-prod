from __future__ import annotations

import csv
import os
import sys
import time
import urllib.request
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
POOL_DIR = ROOT / "pool"
GROUPS_DIR = ROOT / "groups"
OUTPUT_DIR = ROOT / "docs"
OUTPUT_XML = OUTPUT_DIR / "golden1000.xml"
STATUS_JSON = OUTPUT_DIR / "status.json"
INDEX_HTML = OUTPUT_DIR / "index.html"
EXCLUDED_SKUS_FILE = POOL_DIR / "excluded_skus.txt"

MAX_CAPACITY = int(os.environ.get("MAX_CAPACITY", "1000"))
MAX_MISSING_ACTIVE = int(os.environ.get("MAX_MISSING_ACTIVE", "25"))
TIMEOUT_SECONDS = int(os.environ.get("DOWNLOAD_TIMEOUT_SECONDS", "120"))
SIGMA_URL = os.environ.get(
    "SIGMA_FEED_URL",
    "https://sigma.ua/bitrix/catalog_export/marketsigma_ua.php",
).strip()
ZA_URL = os.environ.get("ZAINSTRUMENTOM_FEED_URL", "").strip()
TEKNOSEL_URL = os.environ.get("TEKNOSEL_FEED_URL", "").strip()
GRAND_URL = os.environ.get("GRANDINSTRUMENT_FEED_URL", "").strip()
GPL_URL = os.environ.get("GPL_FEED_URL", "").strip()
PUBLISHED_FEED_URL = os.environ.get(
    "PUBLISHED_FEED_URL",
    "https://yuriimitiaiev-coder.github.io/talpa-golden1000-feed-prod/golden1000.xml",
).strip()
ALLOWED_SUPPLIERS = {"SIGMA", "ZAINSTRUMENTOM", "TEKNOSEL", "GRANDINSTRUMENT", "GPL"}
ALLOWED_STATUSES = {"ACTIVE", "RESERVE"}
GOOGLE_NS = "http://base.google.com/ns/1.0"


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


def parse_xml(data: bytes, label: str) -> etree._Element:
    try:
        return etree.fromstring(data, xml_parser())
    except Exception as exc:
        fail(f"Invalid {label} XML: {exc}")


def get_shop_parts(root: etree._Element, label: str):
    shop = root.find("shop")
    if shop is None:
        fail(f"{label} XML has no <shop>")
    categories = shop.find("categories")
    offers = shop.find("offers")
    if categories is None or offers is None:
        fail(f"{label} XML has no <categories> or <offers>")
    return shop, categories, offers


def download(url: str, label: str, *, optional: bool = False) -> bytes:
    if not url:
        if optional:
            return b""
        fail(f"{label} URL is empty")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TALPA-Golden1000-Controlled-Pool/1.0"},
    )
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                data = resp.read()
            if len(data) < 500:
                raise RuntimeError(f"unexpectedly small response: {len(data)} bytes")
            return data
        except Exception as exc:
            last_exc = exc
            if attempt < 3:
                wait = 10 * attempt
                print(f"WARNING: {label} download failed ({exc}); retry in {wait}s")
                time.sleep(wait)
    if optional:
        print(f"WARNING: optional {label} unavailable: {last_exc}")
        return b""
    fail(f"Cannot download {label}: {last_exc}")


def load_excluded_skus() -> set[str]:
    if not EXCLUDED_SKUS_FILE.exists():
        return set()
    return {
        line.strip()
        for line in EXCLUDED_SKUS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def load_pool() -> list[dict[str, str]]:
    files = sorted(POOL_DIR.glob("catalog_pool_*.csv"))
    if not files:
        fail(f"No catalog pool files in {POOL_DIR}")
    required = {"sku", "supplier", "status", "prom_offer_id", "prom_group_id", "fallback_price"}
    excluded = load_excluded_skus()
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in files:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                fail(f"{path.name} must contain columns {sorted(required)}")
            for raw in reader:
                row = {k: (v or "").strip() for k, v in raw.items()}
                sku = row["sku"]
                if not sku or sku in excluded:
                    continue
                if sku in seen:
                    fail(f"Duplicate SKU in pool: {sku}")
                seen.add(sku)
                row["supplier"] = row["supplier"].upper()
                row["status"] = row["status"].upper()
                if row["supplier"] not in ALLOWED_SUPPLIERS:
                    fail(f"Unknown supplier for {sku}: {row['supplier']!r}")
                if row["status"] not in ALLOWED_STATUSES:
                    fail(f"Unknown status for {sku}: {row['status']!r}")
                rows.append(row)
    if len(rows) > MAX_CAPACITY:
        fail(f"Configured pool has {len(rows)} rows; capacity is {MAX_CAPACITY}")
    active = [r for r in rows if r["status"] == "ACTIVE"]
    if not active:
        fail("Pool contains no ACTIVE products")
    if len(active) > MAX_CAPACITY:
        fail(f"ACTIVE count {len(active)} exceeds capacity {MAX_CAPACITY}")
    return rows


def load_groups() -> dict[str, dict[str, str]]:
    files = sorted(GROUPS_DIR.glob("groups_*.csv"))
    if not files:
        fail(f"No group snapshot files in {GROUPS_DIR}")
    required = {"group_id", "parent_group_id", "name_ua"}
    groups: dict[str, dict[str, str]] = {}
    for path in files:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                fail(f"{path.name} must contain columns {sorted(required)}")
            for raw in reader:
                row = {k: (v or "").strip() for k, v in raw.items()}
                gid = row["group_id"]
                if not gid:
                    continue
                if gid in groups:
                    fail(f"Duplicate group_id: {gid}")
                groups[gid] = row
    for gid, row in groups.items():
        parent = row["parent_group_id"]
        if parent and parent not in groups:
            fail(f"Group {gid} references missing parent {parent}")
    return groups


def supplier_offer_map(data: bytes, label: str) -> dict[str, etree._Element]:
    root = parse_xml(data, label)
    _, _, offers = get_shop_parts(root, label)
    count = len(offers.findall("offer"))
    if count < 100:
        fail(f"{label} feed has too few offers: {count}")
    result: dict[str, etree._Element] = {}
    for offer in offers.findall("offer"):
        sku = (offer.findtext("vendorCode") or "").strip()
        if not sku:
            continue
        previous = result.get(sku)
        if previous is None or (
            previous.get("available") != "true" and offer.get("available") == "true"
        ):
            result[sku] = offer
    return result


def google_merchant_offer_map(data: bytes, label: str) -> dict[str, etree._Element]:
    root = parse_xml(data, label)
    channel = root.find("channel")
    if channel is None:
        fail(f"{label} XML has no <channel>")
    items = channel.findall("item")
    if len(items) < 2:
        fail(f"{label} feed has too few items: {len(items)}")

    g = f"{{{GOOGLE_NS}}}"
    result: dict[str, etree._Element] = {}
    for item in items:
        sku = (item.findtext(f"{g}id") or "").strip()
        if not sku:
            continue
        availability = (item.findtext(f"{g}availability") or "").strip().lower()
        price_raw = (item.findtext(f"{g}price") or "").strip()
        price = price_raw.split()[0].replace(",", ".") if price_raw else ""
        if not price:
            continue

        available = availability == "in stock"
        offer = etree.Element("offer", id=sku, available="true" if available else "false")
        etree.SubElement(offer, "price").text = price
        etree.SubElement(offer, "currencyId").text = "UAH"
        etree.SubElement(offer, "quantity_in_stock").text = "1" if available else "0"
        etree.SubElement(offer, "vendorCode").text = sku

        title = (item.findtext(f"{g}title") or "").strip()
        if title:
            etree.SubElement(offer, "name").text = title
            etree.SubElement(offer, "name_ua").text = title
        brand = (item.findtext(f"{g}brand") or "").strip()
        if brand:
            etree.SubElement(offer, "vendor").text = brand

        result[sku] = offer
    return result


def gpl_offer_map(data: bytes, label: str) -> dict[str, etree._Element]:
    root = parse_xml(data, label)
    channel = root.find("channel")
    if channel is None:
        fail(f"{label} XML has no <channel>")
    items = channel.findall("item")
    if not items:
        fail(f"{label} feed contains no items")

    result: dict[str, etree._Element] = {}
    for item in items:
        sku = (item.findtext("article") or "").strip()
        purchase_price = (item.findtext("price_type_1") or "").strip().replace(",", ".")
        if not sku or not purchase_price:
            continue
        try:
            if float(purchase_price) <= 0:
                continue
        except ValueError:
            continue

        quantity = 0
        for tag in ("warehouse_1", "warehouse_2", "warehouse_4", "warehouse_6"):
            raw = (item.findtext(tag) or "").strip()
            if not raw:
                continue
            if raw.startswith(">"):
                raw = raw[1:].strip()
                try:
                    quantity += int(float(raw)) + 1
                except ValueError:
                    pass
                continue
            try:
                quantity += max(int(float(raw.replace(",", "."))), 0)
            except ValueError:
                pass

        offer = etree.Element("offer", id=sku, available="true" if quantity > 0 else "false")
        etree.SubElement(offer, "price").text = purchase_price
        etree.SubElement(offer, "supplier_price").text = purchase_price
        etree.SubElement(offer, "currencyId").text = "UAH"
        etree.SubElement(offer, "quantity_in_stock").text = str(quantity)
        etree.SubElement(offer, "vendorCode").text = sku

        name = (item.findtext("name") or sku).strip()
        etree.SubElement(offer, "name").text = name
        etree.SubElement(offer, "name_ua").text = name
        brand = (item.findtext("tecdoc_group") or "").strip()
        if brand:
            etree.SubElement(offer, "vendor").text = brand
        image = (item.findtext("image") or "").strip()
        if image:
            etree.SubElement(offer, "picture").text = image
        result[sku] = offer
    return result


def feed_offer_map(data: bytes, label: str) -> dict[str, etree._Element]:
    if not data:
        return {}
    root = parse_xml(data, label)
    _, _, offers = get_shop_parts(root, label)
    result: dict[str, etree._Element] = {}
    for offer in offers.findall("offer"):
        sku = (offer.findtext("vendorCode") or "").strip()
        if sku and sku not in result:
            result[sku] = offer
    return result
