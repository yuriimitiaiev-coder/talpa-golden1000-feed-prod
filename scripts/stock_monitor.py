"""Read-only supplier availability movement monitor. Never modifies a Prom offer."""
import json
import urllib.request
from lxml import etree

SUPPLIERS = ("SIGMA", "ZAINSTRUMENTOM", "GPL", "TEKNOSEL", "GRANDINSTRUMENT")


def fetch_previous_history(published_url):
    url = published_url.rsplit("/", 1)[0] + "/stock_monitor.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TALPA-StockMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            raw = response.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            raise ValueError("history too large")
        report = json.loads(raw)
        history = report.get("history")
        if report.get("schema_version") != 1 or not isinstance(history, list):
            raise ValueError("invalid history schema")
        return history[-42:], True, ""
    except Exception as exc:
        return [], False, f"Previous monitor history unavailable: {exc}"


def _stock(offer):
    if offer is None or offer.get("available") not in {"true", "false"}:
        return None, None
    return offer.get("available") == "true", (offer.findtext("quantity_in_stock") or "").strip()


def build_stock_monitor(rows, xml_bytes, previous_offers, generated_at, *,
                        sigma_feed_source, missing_supplier_skus=(),
                        history=(), history_loaded=False, history_warning=""):
    """Compare FINAL output SKU state against previously published output.

    A zero-movement alert is an advisory freshness anomaly, not proof of bad stock.
    """
    root = etree.fromstring(xml_bytes)
    holder = root.find("shop/offers")
    if holder is None:
        raise ValueError("No offers in generated feed")
    current = {(o.findtext("vendorCode") or "").strip(): o for o in holder.findall("offer")}
    missing = set(missing_supplier_skus)
    previous_record = history[-1] if history_loaded and history else {}
    prev_suppliers = previous_record.get("suppliers", {})
    results = {}
    for supplier in SUPPLIERS:
        results[supplier] = dict(active=0, available=0, unavailable=0, compared=0,
            no_baseline=0, to_available=[], to_unavailable=[], quantity_changed=[],
            mismatched_quantity=[], missing_from_source=[], unchanged_runs=0,
            source_mode=sigma_feed_source if supplier == "SIGMA" else "supplier_feed_download")
    for row in rows:
        sku, supplier = row["sku"], row["supplier"]
        result = results[supplier]
        result["active"] += 1
        if sku not in current:
            raise ValueError(f"Missing generated SKU {sku}")
        now, qty = _stock(current[sku])
        if now is None:
            raise ValueError(f"Missing availability for {sku}")
        result["available" if now else "unavailable"] += 1
        if (now and qty == "0") or (not now and qty not in ("", "0")):
            result["mismatched_quantity"].append(sku)
        if sku in missing:
            result["missing_from_source"].append(sku)
        before, old_qty = _stock(previous_offers.get(sku))
        if before is None:
            result["no_baseline"] += 1
            continue
        result["compared"] += 1
        if before and not now:
            result["to_unavailable"].append(sku)
        if now and not before:
            result["to_available"].append(sku)
        if qty and old_qty and qty != old_qty:
            result["quantity_changed"].append(sku)

    totals = dict(active=0, available=0, unavailable=0, compared=0, no_baseline=0,
                  to_available=0, to_unavailable=0, quantity_changed=0)
    alerts = []
    condensed = {}
    for supplier, result in results.items():
        moved = sum(len(result[k]) for k in ("to_available", "to_unavailable", "quantity_changed"))
        prev = prev_suppliers.get(supplier, {}) if isinstance(prev_suppliers, dict) else {}
        prior_streak = prev.get("unchanged_runs", 0) if isinstance(prev, dict) else 0
        if not isinstance(prior_streak, int):
            prior_streak = 0
        if result["active"] and result["compared"] == result["active"] and moved == 0:
            result["unchanged_runs"] = prior_streak + 1
        for key in totals:
            val = result[key]
            totals[key] += len(val) if isinstance(val, list) else val
        if result["unchanged_runs"] >= 6:
            alerts.append(dict(type="NO_MOVEMENT", supplier=supplier, severity="review",
                               runs=result["unchanged_runs"]))
        if result["mismatched_quantity"]:
            alerts.append(dict(type="STOCK_QUANTITY_CONFLICT", supplier=supplier,
                               severity="warning", skus=result["mismatched_quantity"]))
        if result["missing_from_source"]:
            alerts.append(dict(type="MISSING_SUPPLIER_SKUS", supplier=supplier,
                               severity="warning", skus=result["missing_from_source"]))
        condensed[supplier] = {k: (len(result[k]) if isinstance(result[k], list) else result[k])
            for k in ("active", "available", "unavailable", "compared",
                      "to_available", "to_unavailable", "quantity_changed",
                      "unchanged_runs", "source_mode")}
    if sigma_feed_source != "live" and results["SIGMA"]["active"]:
        alerts.append(dict(type="SIGMA_SNAPSHOT_FALLBACK", supplier="SIGMA", severity="warning"))
    if not previous_offers:
        alerts.append(dict(type="NO_BASELINE_XML", severity="review"))
    if not history_loaded:
        alerts.append(dict(type="HISTORY_UNAVAILABLE", severity="review", message=history_warning))
    new_history = (list(history) if history_loaded else []) + [
        dict(generated_at_utc=generated_at, suppliers=condensed)]
    return dict(schema_version=1, generated_at_utc=generated_at,
                baseline_feed_available=bool(previous_offers),
                history_loaded=history_loaded, history_window_runs=42,
                totals=totals, by_supplier=results, alerts=alerts, history=new_history[-42:])
