#!/usr/bin/env python3
"""Create standalone 35-product YML for one-time Prom *creation* after Grand deletion.
NEVER automatically import. SIGMA photos use supplier originals in this temporary
file because new TALPA-mirrored Pages images are not live before the new deployment.
"""
import csv
import copy
from pathlib import Path
from lxml import etree
from pool_common import ROOT,SIGMA_URL,download,supplier_offer_map
ROOT=Path(__file__).resolve().parents[1]
with (ROOT/"data/grand35_replacement_selected.csv").open(newline="",encoding="utf-8-sig") as fh:
    new=list(csv.DictReader(fh))
assert len(new)==35 and len({r["sku"] for r in new})==35
original=etree.parse(str(ROOT/"docs/golden1000.xml"))
root=original.getroot()
shop=root.find("shop")
assert shop is not None
offers=shop.find("offers")
assert offers is not None
existing={(x.findtext("vendorCode") or "").strip():x for x in offers.findall("offer")}
assert len(existing)==980
sigma=supplier_offer_map(download(SIGMA_URL,"SIGMA"),"SIGMA")
fresh=[]
for r in new:
    sku=r["sku"];offer=existing.get(sku)
    assert offer is not None,(sku,"missing in staging")
    clone=copy.deepcopy(offer)
    if r["supplier"]=="SIGMA":
        source=sigma.get(sku)
        assert source is not None
        pic=[copy.deepcopy(x) for x in source.findall("picture") if (x.text or "").strip()][:10]
        assert pic,(sku,"source photo missing")
        for p in clone.findall("picture"):clone.remove(p)
        for p in pic:clone.append(p)
    assert clone.get("id")==sku,(sku,"offer id must be stable new SKU")
    assert (clone.findtext("name") or "").strip() not in ("",sku),(sku,"name missing")
    assert len(clone.findall("picture"))>0,(sku,"photo missing")
    assert float(clone.findtext("price") or "0")>0,(sku,"retail price")
    fresh.append(clone)
for node in offers.findall("offer"):offers.remove(node)
for clone in fresh:offers.append(clone)
target=ROOT/"staging/grand35_add_35_only_PROM_IMPORT.xml"
target.parent.mkdir(parents=True,exist_ok=True)
original.write(str(target),xml_declaration=True,encoding="utf-8",pretty_print=True)
tree=etree.parse(str(target))
assert len(tree.findall(".//offers/offer"))==35
print("ONE_TIME_PROM_35_ONLY_IMPORT="+str(target.relative_to(ROOT))+" offers=35, no old Grand SKUs")
