#!/usr/bin/env python3
"""Read-only Golden980 generated XML gate. A failure prohibits deployment."""
from __future__ import annotations
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path
from lxml import etree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pool_common import load_pool
root=Path(__file__).resolve().parents[1]
v2=root/"data/approved_golden980_v2_PENDING_PROM_UID.csv"
master_file=v2 if v2.exists() else root/"data/approved_golden980_2026-11-01.csv"
staging=os.environ.get("GRAND35_STAGING","")=="1"
with master_file.open(newline="",encoding="utf-8") as f:
    master=list(csv.DictReader(f))
pool=load_pool()
active=[r for r in pool if r["status"]=="ACTIVE"]
assert len(master)==len(pool)==len(active)==980,"980 ACTIVE expected"
assert len({r["sku"] for r in master})==980,"duplicate master SKU"
expected_suppliers={"SIGMA":655,"ZAINSTRUMENTOM":325} if v2.exists() else {"SIGMA":632,"ZAINSTRUMENTOM":313,"GRANDINSTRUMENT":35}
assert Counter(r["supplier"] for r in active)==expected_suppliers
pending=[r for r in master if not r["prom_uid"]]
if pending and not staging:
    raise AssertionError("PRODUCTION HOLD: new products have no confirmed Prom internal UID")
if pending:
    assert v2.exists() and len(pending)==35,"Exactly 35 newly staged SKU expected"
assert len({r["external_id"] for r in master})==980,"all 980 external ID must be unique"
assert len({r["prom_offer_id"] for r in active})==980
approved={r["sku"]:r for r in master}
assert {r["sku"] for r in active}==set(approved)
for r in active:
    assert r["prom_offer_id"]==(approved[r["sku"]]["external_id"] or approved[r["sku"]]["prom_uid"]),r["sku"]
    assert r["prom_group_id"],r["sku"]
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
new_skus={r["sku"] for r in pending}
for offer in offers:
    sku=(offer.findtext("vendorCode") or "").strip()
    assert (offer.findtext("categoryId") or "").strip()==groups[sku],sku
    if sku in new_skus:
        assert (offer.findtext("name") or "").strip() not in ("",sku),(sku,"missing name")
        assert any((p.text or "").strip() for p in offer.findall("picture")),(sku,"missing photo")
    price=float((offer.findtext("price") or "0").replace(",","."))
    qty=float((offer.findtext("quantity_in_stock") or "-1").replace(",","."))
    assert price>0 and qty>=0,(sku,price,qty)
    if offer.get("available")=="false":
        assert qty==0,(sku,"unavailable must mean zero")
print(json.dumps({"result":"STAGING_PASS_PENDING_PROM_UID" if pending else "PASS","active":980,"reserve_capacity":20,"prom_uid_pending":len(pending),"suppliers":dict(Counter(r["supplier"] for r in active))},ensure_ascii=False))
