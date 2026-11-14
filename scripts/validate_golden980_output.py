#!/usr/bin/env python3
"""Read-only Golden980 generated XML gate. A failure prohibits deployment."""
from __future__ import annotations
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from lxml import etree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pool_common import load_pool
root=Path(__file__).resolve().parents[1]
with (root/"data/golden980_target_2026-11-10.csv").open(newline="",encoding="utf-8") as f:
    master=list(csv.DictReader(f))
pool=load_pool()
active=[r for r in pool if r["status"]=="ACTIVE"]
assert len(master)==len(pool)==len(active)==980,"980 ACTIVE expected"
assert len({r["sku"] for r in master})==980,"duplicate master SKU"
assert Counter(r["supplier"] for r in active)=={"SIGMA":559,"ZAINSTRUMENTOM":421}
assert len({r["prom_offer_id"] for r in active})==980
approved={r["sku"]:r for r in master}
assert {r["sku"] for r in active}==set(approved)
for r in active:
    assert r["prom_offer_id"]==approved[r["sku"]]["prom_offer_id"],r["sku"]
    assert r["prom_group_id"],r["sku"]
    assert r["supplier"]==approved[r["sku"]]["supplier"],r["sku"]
    assert r["prom_group_id"]==approved[r["sku"]]["prom_group_id"],r["sku"]
    assert r["status"]=="ACTIVE",r["sku"]
status=json.loads((root/"docs/status.json").read_text(encoding="utf-8"))
stock=json.loads((root/"docs/stock_monitor.json").read_text(encoding="utf-8"))
assert status["active"]==status["offers"]==980,status
assert status["pool_configured"]==980,status
assert status["reserve_configured"]==0,status
assert status["free_slots"]==20,status
assert stock["totals"]["active"]==980,stock["totals"]
assert stock["totals"]["available"]+stock["totals"]["unavailable"]==980,stock["totals"]
assert status["sigma_feed_source"] in {"live","published_snapshot"}
assert status["sigma_feed_snapshot_bytes"]>100000
doc=etree.parse(str(root/"docs/golden1000.xml"))
offers=doc.find("shop").find("offers").findall("offer")
assert len(offers)==980,len(offers)
codes=[(o.findtext("vendorCode") or "").strip() for o in offers]
ids=[(o.get("id") or "").strip() for o in offers]
assert len(set(codes))==len(set(ids))==980
assert codes==[r["sku"] for r in active],"offer SKUs do not match approved order"
assert ids==[r["prom_offer_id"] for r in active],"offer id must preserve Prom external id"
groups={r["sku"]:r["prom_group_id"] for r in active}
for offer in offers:
    sku=(offer.findtext("vendorCode") or "").strip()
    assert (offer.findtext("categoryId") or "").strip()==groups[sku],sku
    price=float((offer.findtext("price") or "0").replace(",","."))
    qty=float((offer.findtext("quantity_in_stock") or "-1").replace(",","."))
    assert price>0 and qty>=0,(sku,price,qty)
    if offer.get("available")=="false":
        assert qty==0,(sku,"unavailable must mean zero")
# Golden980 November 2026 rotation: structural and preview safety gates.
# All 34 additions must have name and photograph; a missing supplier source
# cannot silently create a placeholder card that Prom would accept as a product.
new_skus=set(["6010521","6049131","4008531","4242461","4372411","5022344","5021132","108021","4401642","2622011","1520161","205250-2К","4241361","4401522","6034081","12325","1811491","1811551","4102761","1301321","1513061","5022474","6022221","4102771","1919262","1922071","4372441","1513051","4009021","4102522","4100212","1186081","1918822","5024564"])
assert new_skus.issubset(set(codes)),sorted(new_skus-set(codes))
for offer in offers:
    sku=(offer.findtext("vendorCode") or "").strip()
    if sku in new_skus:
        title=(offer.findtext("name_ua") or offer.findtext("name") or "").strip()
        pictures=[(p.text or "").strip() for p in offer.findall("picture") if (p.text or "").strip()]
        assert title and title!=sku,(sku,"missing real supplier title")
        assert pictures,(sku,"missing photograph")
        # Initial PR test only: do not block scheduled updates when stock later falls to zero.
        if __import__("os").environ.get("GITHUB_EVENT_NAME")=="pull_request":
            assert offer.get("available")=="true" and float(offer.findtext("quantity_in_stock") or "0")>0,(sku,"not available for first publication")
print(json.dumps({"result":"PASS","active":980,"reserve_capacity":20,"suppliers":dict(Counter(r["supplier"] for r in active))},ensure_ascii=False))
