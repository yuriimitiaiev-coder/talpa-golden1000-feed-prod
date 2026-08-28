from __future__ import annotations

from lxml import etree


def _as_positive_float(text: str | None) -> float | None:
    raw = (text or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def normalize_zainstrumentom_promotions(
    offers_by_sku: dict[str, etree._Element],
) -> list[dict[str, str]]:
    """Protect TALPA from supplier retail promotions being treated as base RRP.

    ZaInstrumentom confirmed that when its retail feed carries a temporary
    discount, the ordinary OPT/DROP discount does not stack on top of that
    promotional price. For TALPA, such a promotional price must therefore not
    automatically become the Prom.ua selling base.

    Prom/YML normally represents this as:
      <price>current promotional retail price</price>
      <oldprice>regular RRP</oldprice>

    For every ZaInstrumentom offer where oldprice > price, this guard restores
    the regular RRP into <price> and removes promotion markers before the
    controlled Golden1000 feed is built.

    Returns a list of adjusted SKUs for audit/status reporting.
    """
    adjusted: list[dict[str, str]] = []

    for sku, offer in offers_by_sku.items():
        price_node = offer.find("price")
        oldprice_node = offer.find("oldprice")
        if price_node is None or oldprice_node is None:
            continue

        promo_price = _as_positive_float(price_node.text)
        rrp = _as_positive_float(oldprice_node.text)
        if promo_price is None or rrp is None or rrp <= promo_price:
            continue

        price_node.text = (oldprice_node.text or "").strip().replace(",", ".")

        # The output feed must carry the regular RRP as its base price, not a
        # supplier promotion. Remove all supplier promotion markers so Prom.ua
        # does not recreate the temporary discount automatically.
        for tag in ("oldprice", "discount"):
            for node in list(offer.findall(tag)):
                offer.remove(node)

        adjusted.append(
            {
                "sku": sku,
                "supplier_promo_price": f"{promo_price:.2f}",
                "rrp": f"{rrp:.2f}",
            }
        )

    return adjusted
