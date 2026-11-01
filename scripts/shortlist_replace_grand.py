#!/usr/bin/env python3
"""Read-only candidate finder for replacement of 35 Grand Instrument Golden980 SKUs.
Uses live Sigma and ZaInstrumentom supplier data, never publishes or edits Prom.
Prices are supplier selling/RRP; procurement margin is NOT asserted.
"""
import csv
import json
import re
import sys
from collections import Counter,defaultdict
from pathlib import Path
from lxml import etree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pool_common import ROOT, SIGMA_URL, ZA_URL,download,load_pool,supplier_offer_map,parse_xml,get_shop_parts
TOP=int(__import__("os").environ.get("TOP_REPLACEMENT_CANDIDATES","125"))
OLD_EXCLUDED=ROOT/"pool"/"excluded_skus.txt"

def normalized(txt):
    return re.sub(r"\s+"," ",(txt or "")).strip()

def to_price(s):
    try:
        x=float(normalized(s).replace(",","."))
        return round(x,2) if x>0 else None
    except ValueError:
        return None

def main():
    existing=load_pool()
    existing_skus={r["sku"] for r in existing}
    excluded={x.strip() for x in OLD_EXCLUDED.read_text().splitlines() if x.strip() and not x.startswith("#")}
    lookups={}
    raw_data={}
    for supplier,url,label in [("SIGMA",SIGMA_URL,"SIGMA"),("ZAINSTRUMENTOM",ZA_URL,"ZaInstrumentom")]:
        data=download(url,label)
        raw_data[supplier]=data
        lookups[supplier]=supplier_offer_map(data,label)
    # Recover supplier-native category -> matching TALPA group based on currently
    # accepted products. Only unambiguous mappings are eligible for automatic staging.
    categories=defaultdict(lambda: defaultdict(Counter))
    for row in existing:
        supplier=row["supplier"]
        if supplier not in lookups:continue
        src=lookups[supplier].get(row["sku"])
        if src is None: continue
        native=normalized(src.findtext("categoryId"))
        if native and row["prom_group_id"]:
            categories[supplier][native][row["prom_group_id"]]+=1
    unique_group={}
    for supplier,mp in categories.items():
        unique_group[supplier]={category:count.most_common(1)[0][0] for category,count in mp.items() if len(count)==1 and sum(count.values())>=1}
    print("CATEGORY_MAPPING_STATS="+json.dumps({s:{"native_categories":len(categories[s]),"unique_mappings":len(unique_group[s])}for s in lookups}))
    # Check previously researched high-demand candidates against today's live feed.
    previously_ranked = {
      "ZAINSTRUMENTOM":["YT-3259","YT-81440","YT-3308","YT-82781","2-14-563",
        "48081","YT-24095","140751330","YT-827790","YT-82787","YT-82036",
        "102441","FO-4031","030-0474","10018202","P240W"],
      "SIGMA":["4002912","9410911","9418541","6003055","9449701"],
    }
    for supplier, skus in previously_ranked.items():
        for sku in skus:
            src=lookups[supplier].get(sku)
            if src is None:
                report={"supplier":supplier,"sku":sku,"live":False}
            else:
                native=normalized(src.findtext("categoryId"))
                report={"supplier":supplier,"sku":sku,"live":True,
                    "available":src.get("available")=="true",
                    "already_in_catalog":sku in existing_skus,
                    "historically_excluded":sku in excluded,
                    "price":to_price(src.findtext("price")),
                    "quantity":normalized(src.findtext("quantity_in_stock")),
                    "group":unique_group[supplier].get(native,""),
                    "photos":len(src.findall("picture")),
                    "name":normalized(src.findtext("name_ua") or src.findtext("name"))[:100]}
            print("PRIOR_RANKED="+json.dumps(report,ensure_ascii=False))
    patterns=[
        ("consumables",r"(біт|насадк|свердл|бур\b|свердел|диск|круг\b|круги|шліф|абразив|лезо|ножівк|стяжк|клем|полотн|витратн|головк|коронк|біти\b|bit\b|drill)",10),
        ("hand_tools",r"(ключ\b|ключі|викрутк|рулетк|кусачк|плоскогуб|кліщ|щипц|молот|стамеск|рівень|рівн\b|кельм|шпател|пістолет|степлер|пилка|ножиці|ніж\b)",8),
        ("power_tools",r"(шуруповерт|перфоратор|шліфмашин|дрил|лобзик|реноватор|гайковерт|фен\b|болгарк)",7),
        ("workshop",r"(струбцин|тиск|ліщат|тріскач|трещотк|напил|шестигран|торкс|зубил|вимірюв|розмітк|монтаж)",6)
    ]
    exclude_re=re.compile(r"(ванн|душов|полив|басейн|посуд|автокосмет|пральн|чистяч|косметик|ароматиз|пестицид|септик|декор|вазон|пляж|садовий шланг|шланг для полив|дитяч|кухон)",re.I)
    records=[]
    for supplier,mp in lookups.items():
        for sku,o in mp.items():
            if sku in existing_skus or sku in excluded: continue
            if o.get("available")!="true":continue
            name=normalized(o.findtext("name_ua") or o.findtext("name"))
            if len(name)<14 or exclude_re.search(name):continue
            matches=[(tag,weight) for tag,rgx,weight in patterns if re.search(rgx,name,re.I)]
            if not matches:continue
            price=to_price(o.findtext("price"))
            if price is None or price<125 or price>6500:continue
            pics=[normalized(x.text) for x in o.findall("picture") if normalized(x.text)]
            if not pics:continue
            native=normalized(o.findtext("categoryId"))
            group=unique_group.get(supplier,{}).get(native)
            raw_qty=normalized(o.findtext("quantity_in_stock"))
            try: qty=int(float(raw_qty.replace(",","."))) if raw_qty else None
            except ValueError:qty=None
            if supplier=="ZAINSTRUMENTOM" and qty is not None and qty<3:continue
            score=(matches[0][1]*10) + (15 if 250<=price<=1600 else 8 if 1600<price<=3500 else 0)
            if supplier=="ZAINSTRUMENTOM" and qty is not None:score+=min(20,qty)
            if group:score+=15
            score+=min(10,len(pics)*2)
            records.append({"supplier":supplier,"sku":sku,"name":name[:150],"price_rrc":price,
                            "available":1,"quantity":qty if qty is not None else "unknown",
                            "supplier_group_id":native,"prom_group_id":group or "",
                            "picture_count":len(pics),"picture_url":pics[0],
                            "category":matches[0][0],"score":score,
                            "group_verified":"ONE_TO_ONE" if group else "REVIEW"})
    records.sort(key=lambda x:(-x["score"],x["supplier"],x["sku"]))
    print("CANDIDATE_COUNTS="+json.dumps({"total":len(records),"by_supplier":dict(Counter(x["supplier"]for x in records)),
        "group_mapped":dict(Counter(x["supplier"] for x in records if x["prom_group_id"]))},ensure_ascii=False))
    # Print enough human-readable rows to allow a reasoned, diverse 35-SKU choice.
    for supplier in ("SIGMA","ZAINSTRUMENTOM"):
        displayed=0
        for r in records:
            if r["supplier"]!=supplier:continue
            if displayed>=TOP:break
            print("CANDIDATE="+json.dumps({k:v for k,v in r.items() if k!="picture_url"},ensure_ascii=False))
            displayed+=1
    out=ROOT/"data"/"grand35_replacement_live_candidates.csv"
    cols=["supplier","sku","name","price_rrc","available","quantity","supplier_group_id","prom_group_id","picture_count","picture_url","category","score","group_verified"]
    with out.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(records)
    print("SHORTLIST_FILE="+str(out.relative_to(ROOT)))

if __name__=="__main__":
    main()
