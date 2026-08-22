from __future__ import annotations

import re
from lxml import etree

WRONG_BFC4000_IMAGE_MARKER = "GRZECHOTKA-PNEUMATYCZNA-KLUCZ-KATOWY"
_WRONG_BFC4000_IMAGE_RE = re.compile(
    r"<img\b[^>]*GRZECHOTKA-PNEUMATYCZNA-KLUCZ-KATOWY[^>]*?/?>",
    flags=re.IGNORECASE,
)
_EMPTY_PARAGRAPH_RE = re.compile(r"<p>\s*</p>", flags=re.IGNORECASE)


def _patch_description(text: str, sku: str) -> str:
    if sku == "AHC48-K":
        return text.replace("AHC48-J", "AHC48-K")
    if sku == "BFC4000":
        cleaned = _WRONG_BFC4000_IMAGE_RE.sub("", text)
        return _EMPTY_PARAGRAPH_RE.sub("", cleaned)
    return text


def patch_grand_content(offer_map: dict[str, etree._Element]) -> None:
    """Apply narrowly scoped TALPA content corrections to known Grand Instrument feed defects."""
    for sku in ("AHC48-K", "BFC4000"):
        offer = offer_map.get(sku)
        if offer is None:
            continue
        for tag in ("description", "description_ua"):
            node = offer.find(tag)
            if node is not None and node.text:
                node.text = _patch_description(node.text, sku)


def validate_grand_output(xml_bytes: bytes) -> None:
    """Fail the build if the two verified supplier-content defects leak into generated output."""
    root = etree.fromstring(xml_bytes)
    shop = root.find("shop")
    offers_node = shop.find("offers") if shop is not None else None
    if offers_node is None:
        raise RuntimeError("Generated XML has no offers node")

    by_sku = {
        (offer.findtext("vendorCode") or "").strip(): offer
        for offer in offers_node.findall("offer")
    }

    ahc = by_sku.get("AHC48-K")
    if ahc is not None:
        text = "\n".join((ahc.findtext(tag) or "") for tag in ("description", "description_ua"))
        if "AHC48-J" in text:
            raise RuntimeError("AHC48-K generated content still contains wrong model AHC48-J")

    bfc = by_sku.get("BFC4000")
    if bfc is not None:
        text = "\n".join((bfc.findtext(tag) or "") for tag in ("description", "description_ua"))
        if WRONG_BFC4000_IMAGE_MARKER.lower() in text.lower():
            raise RuntimeError("BFC4000 generated content still contains unrelated ratchet image")
