#!/usr/bin/env python3
"""Read-only audit for Grand Instrument XML price field interpretation.

Do not infer recommended retail prices from wholesale values. This audit prints
field names and aggregated ratios only, never supplier credentials or item prices.
"""
from __future__ import annotations
import json
from collections import Counter
from statistics import median

def audit_grand_rrp(pool, grand_map) -> None:
    grand=[r for r in pool if r["status"]=="ACTIVE" and r["supplier"]=="GRANDINSTRUMENT"]
    all_fields=Counter()
    ratios=[]
    match=0
    lower=0
    greater=0
    identical=0
    missing=0
    for row in grand:
        src=grand_map.get(row["sku"])
        if src is None:
            missing+=1
            continue
        all_fields.update(ch.tag for ch in src if isinstance(ch.tag,str))
        try:
            feed=float((src.findtext("price") or "").strip().replace(",","."))
            fallback=float((row["fallback_price"] or "").strip().replace(",","."))
            if feed<=0 or fallback<=0: continue
        except ValueError:
            continue
        ratios.append(round(fallback/feed,4))
        if abs(fallback-feed)<0.011: identical+=1
        elif fallback>feed: greater+=1
        else: lower+=1
        match+=1
    report={
        "grand_sku_total":len(grand),
        "found_in_live_feed":len(grand)-missing,
        "matched_price_pairs":match,
        "live_xml_element_names":sorted(all_fields),
        "fallback_equals_feed_price":identical,
        "fallback_greater_than_feed_price":greater,
        "fallback_less_than_feed_price":lower,
        "fallback_over_feed_price_median":round(median(ratios),4) if ratios else None,
        "fallback_over_feed_price_min":min(ratios) if ratios else None,
        "fallback_over_feed_price_max":max(ratios) if ratios else None,
        "price_source_classification":"UNVERIFIED_RRP_DO_NOT_AUTO_SWITCH",
    }
    print("GRAND_RRP_FIELD_AUDIT="+json.dumps(report,ensure_ascii=False))
