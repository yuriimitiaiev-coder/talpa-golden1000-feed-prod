from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from lxml import etree

from pool_common import MAX_CAPACITY, MAX_MISSING_ACTIVE, fail, get_shop_parts, parse_xml


def set_child_text(parent: etree._Element, tag: str, value: str) -> etree._Element:
    node = parent.find(tag)
    if node is None:
        node = etree.Element(tag)
        parent.append(node)
    node.text = value
    return node


def remove_children(parent: etree._Element, tags: tuple[str, ...]) -> None:
    for tag in tags:
        for node in list(parent.findall(tag)):
            parent.remove(node)


def normalized_price(source: etree._Element, sku: str) -> str:
    raw = (source.findtext("price") or "").strip().replace(",", ".")
    try:
        value = float(raw)
    except Exception:
        fail(f"Invalid supplier price for {sku}: {raw!r}")
    if value <= 0:
        fail(f"Non-positive supplier price for {sku}: {raw!r}")
    return raw


def effective_selling_price(source: etree._Element, row: dict[str, str]) -> str:
    sku = row["sku"]
    if row["supplier"] in {"GRANDINSTRUMENT", "GPL"}:
        raw = row["fallback_price"].replace(",", ".").strip()
        try:
            value = float(raw)
        except Exception:
            fail(f"Invalid controlled selling price for {sku}: {raw!r}")
        if value <= 0:
            fail(f"Non-positive controlled selling price for {sku}: {raw!r}")
        return raw
    return normalized_price(source, sku)


def source_quantity(source: etree._Element, supplier: str, available: bool) -> str:
    if not available:
        return "0"
    if supplier in {"SIGMA", "TEKNOSEL"}:
        return "1"
    raw = (source.findtext("quantity_in_stock") or "").strip()
    if not raw:
        return "1"
    try:
        return str(max(int(float(raw.replace(",", "."))), 0))
    except Exception:
        return "1"


def force_unavailable(offer: etree._Element) -> etree._Element:
    out = copy.deepcopy(offer)
    out.set("available", "false")
    out.attrib.pop("in_stock", None)
    remove_children(out, ("oldprice", "discount", "in_stock"))
    set_child_text(out, "quantity_in_stock", "0")
    for tag in ("quantity", "stock_quantity", "amount"):
        node = out.find(tag)
        if node is not None:
            node.text = "0"
    return out


def build_new_structural_offer(source: etree._Element, row: dict[str, str]) -> etree._Element:
    sku = row["sku"]
    group_id = row["prom_group_id"]
    if not group_id:
        fail(f"New ACTIVE SKU {sku} requires prom_group_id")
    offer_id = row["prom_offer_id"] or (source.get("id") or "").strip() or sku
    out = etree.Element("offer", id=offer_id)
    for tag in (
        "url", "picture", "name", "name_ua", "vendor",
        "description", "description_ua", "country_of_origin", "portal_category_url", "param",
    ):
        nodes = source.findall(tag)
        if tag == "picture":
            nodes = nodes[:10]
        for node in nodes:
            cloned = copy.deepcopy(node)
            if tag in {"name", "name_ua"} and cloned.text:
                cloned.text = cloned.text.strip()[:90]
            out.append(cloned)
    if out.find("name") is None:
        set_child_text(out, "name", sku)
    set_child_text(out, "categoryId", group_id)
    set_child_text(out, "vendorCode", sku)
    return out


def build_controller_offer(row: dict[str, str]) -> etree._Element:
    sku = row["sku"]
    offer_id = row["prom_offer_id"]
    group_id = row["prom_group_id"]
    price = row["fallback_price"].replace(",", ".").strip()
    if not offer_id or not group_id:
        fail(f"Existing ACTIVE SKU {sku} requires prom_offer_id and prom_group_id")
    try:
        if float(price) <= 0:
            raise ValueError
    except Exception:
        fail(f"Invalid fallback_price for {sku}: {price!r}")
    name = row.get("fallback_name") or sku
    out = etree.Element("offer", id=offer_id, available="true")
    set_child_text(out, "price", price)
    set_child_text(out, "currencyId", "UAH")
    set_child_text(out, "quantity_in_stock", "1")
    set_child_text(out, "categoryId", group_id)
    set_child_text(out, "name", name[:90])
    set_child_text(out, "name_ua", name[:90])
    set_child_text(out, "vendorCode", sku)
    return out


def overlay_commercial(base: etree._Element, source: etree._Element, row: dict[str, str]) -> etree._Element:
    sku = row["sku"]
    supplier = row["supplier"]
    out = copy.deepcopy(base)
    configured_id = row["prom_offer_id"]
    if configured_id:
        out.set("id", configured_id)
    elif not out.get("id"):
        out.set("id", (source.get("id") or "").strip() or sku)
    set_child_text(out, "vendorCode", sku)

    name = out.find("name")
    if name is None or not (name.text or "").strip() or (name.text or "").strip() == sku:
        source_name = (source.findtext("name") or source.findtext("name_ua") or sku).strip()
        set_child_text(out, "name", source_name[:90])
    name_ua = out.find("name_ua")
    if name_ua is None or not (name_ua.text or "").strip() or (name_ua.text or "").strip() == sku:
        source_name_ua = (source.findtext("name_ua") or source.findtext("name") or sku).strip()
        set_child_text(out, "name_ua", source_name_ua[:90])

    group_id = row["prom_group_id"]
    if group_id:
        set_child_text(out, "categoryId", group_id)
    available = source.get("available") == "true"
    out.set("available", "true" if available else "false")
    out.attrib.pop("in_stock", None)
    remove_children(out, ("oldprice", "discount", "in_stock"))
    set_child_text(out, "price", effective_selling_price(source, row))
    set_child_text(out, "currencyId", (source.findtext("currencyId") or "UAH").strip() or "UAH")
    q = source_quantity(source, supplier, available)
    set_child_text(out, "quantity_in_stock", q)
    for tag in ("quantity", "stock_quantity", "amount"):
        node = out.find(tag)
        if node is not None:
            node.text = q
    return out


def category_ids_needed(active_rows, groups) -> set[str]:
    needed: set[str] = set()
    for row in active_rows:
        gid = row["prom_group_id"]
        if not gid:
            continue
        if gid not in groups:
            fail(f"SKU {row['sku']} references unknown prom_group_id {gid}")
        seen: set[str] = set()
        while gid:
            if gid in seen:
                fail(f"Cycle in group hierarchy at {gid}")
            seen.add(gid)
            needed.add(gid)
            gid = groups[gid]["parent_group_id"]
    return needed


def build_xml(active_rows, groups, published_map, sigma_map, za_map, teknosel_map, grand_map, gpl_map):
    missing: list[str] = []
    new_structural: list[str] = []
    output_offers: list[etree._Element] = []
    seen_offer_ids: set[str] = set()
    source_maps = {
        "SIGMA": sigma_map,
        "ZAINSTRUMENTOM": za_map,
        "TEKNOSEL": teknosel_map,
        "GRANDINSTRUMENT": grand_map,
        "GPL": gpl_map,
    }

    for row in active_rows:
        sku = row["sku"]
        source = source_maps[row["supplier"]].get(sku)
        previous = build_controller_offer(row) if row["prom_offer_id"] else published_map.get(sku)

        if source is None:
            if previous is None:
                fail(f"ACTIVE SKU {sku} is absent from supplier feed and has no fallback card")
            out = force_unavailable(previous)
            if row["prom_group_id"]:
                set_child_text(out, "categoryId", row["prom_group_id"])
            set_child_text(out, "vendorCode", sku)
            missing.append(sku)
        else:
            if previous is None:
                previous = build_new_structural_offer(source, row)
                new_structural.append(sku)
            out = overlay_commercial(previous, source, row)

        oid = (out.get("id") or "").strip()
        if not oid:
            fail(f"Generated SKU {sku} has empty offer id")
        if oid in seen_offer_ids:
            fail(f"Duplicate generated offer id: {oid}")
        seen_offer_ids.add(oid)
        output_offers.append(out)

    if len(missing) > MAX_MISSING_ACTIVE:
        fail(f"Supplier feeds are missing {len(missing)} ACTIVE SKUs; limit is {MAX_MISSING_ACTIVE}")

    needed = category_ids_needed(active_rows, groups)
    root = etree.Element("yml_catalog", date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    shop = etree.SubElement(root, "shop")
    etree.SubElement(shop, "name").text = "TALPA Golden1000 Controlled Pool"
    etree.SubElement(shop, "company").text = "ТОВ «ТАЛПА ІНДАСТРІАЛ КОМПОНЕНТС»"
    etree.SubElement(shop, "url").text = "https://prom.ua/ua/c4220125-talpa-tehnichni-tovari.html"
    currencies = etree.SubElement(shop, "currencies")
    etree.SubElement(currencies, "currency", id="UAH", rate="1")
    categories = etree.SubElement(shop, "categories")
    for gid, row in groups.items():
        if gid not in needed:
            continue
        attrs = {"id": gid}
        parent = row["parent_group_id"]
        if parent and parent in needed:
            attrs["parentId"] = parent
        node = etree.SubElement(categories, "category", **attrs)
        node.text = row.get("name_ua") or row.get("name") or gid
    offers_node = etree.SubElement(shop, "offers")
    for offer in output_offers:
        offers_node.append(offer)

    xml_bytes = etree.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    check_root = parse_xml(xml_bytes, "generated")
    _, check_categories, check_offers = get_shop_parts(check_root, "generated")
    check_codes = [(o.findtext("vendorCode") or "").strip() for o in check_offers.findall("offer")]
    wanted = [r["sku"] for r in active_rows]
    if check_codes != wanted:
        fail("Generated SKU order/content differs from ACTIVE pool")
    if len(set(check_codes)) != len(check_codes):
        fail("Generated feed has duplicate SKU values")
    if len(check_codes) > MAX_CAPACITY:
        fail(f"Generated feed has {len(check_codes)} offers; capacity is {MAX_CAPACITY}")

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "capacity": MAX_CAPACITY,
        "offers": len(check_codes),
        "active": len(active_rows),
        "sigma_active": sum(r["supplier"] == "SIGMA" for r in active_rows),
        "zainstrumentom_active": sum(r["supplier"] == "ZAINSTRUMENTOM" for r in active_rows),
        "teknosel_active": sum(r["supplier"] == "TEKNOSEL" for r in active_rows),
        "grandinstrument_active": sum(r["supplier"] == "GRANDINSTRUMENT" for r in active_rows),
        "gpl_active": sum(r["supplier"] == "GPL" for r in active_rows),
        "supplier_missing_active": sorted(missing),
        "supplier_missing_count": len(missing),
        "new_structural_cards": sorted(new_structural),
        "categories": len(check_categories.findall("category")),
        "output_bytes": len(xml_bytes),
        "sha256": hashlib.sha256(xml_bytes).hexdigest(),
    }
    return xml_bytes, metadata
