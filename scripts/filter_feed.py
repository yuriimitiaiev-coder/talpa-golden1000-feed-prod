#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, sys, tempfile, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
CODES_FILE=ROOT/'golden_codes.txt'; OUTPUT_DIR=ROOT/'docs'; OUTPUT_XML=OUTPUT_DIR/'golden1000.xml'; STATUS_JSON=OUTPUT_DIR/'status.json'; INDEX_HTML=OUTPUT_DIR/'index.html'
SOURCE_URL=os.environ.get('SOURCE_FEED_URL','').strip(); EXPECTED_COUNT=int(os.environ.get('EXPECTED_COUNT','1000')); TIMEOUT=int(os.environ.get('DOWNLOAD_TIMEOUT_SECONDS','120'))
def fail(msg): print('ERROR:',msg,file=sys.stderr); raise SystemExit(1)
def load_codes():
    codes={x.strip() for x in CODES_FILE.read_text(encoding='utf-8').splitlines() if x.strip() and not x.lstrip().startswith('#')}
    if len(codes)!=EXPECTED_COUNT: fail(f'Expected {EXPECTED_COUNT} codes, got {len(codes)}')
    return codes
def download(url):
    if not url: fail('SOURCE_FEED_URL is empty')
    req=urllib.request.Request(url,headers={'User-Agent':'TALPA-Golden1000-Filter/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=TIMEOUT) as r: data=r.read()
    except Exception as e: fail(f'Cannot download source feed: {e}')
    if len(data)<1000: fail(f'Feed too small: {len(data)} bytes')
    return data
def build(source,wanted):
    parser=etree.XMLParser(strip_cdata=False,remove_blank_text=False,recover=False,resolve_entities=False,no_network=True,huge_tree=True)
    try: root=etree.fromstring(source,parser)
    except Exception as e: fail(f'Invalid source XML: {e}')
    shop=root.find('shop');
    if shop is None: fail('No <shop>')
    categories=shop.find('categories'); offers=shop.find('offers')
    if categories is None or offers is None: fail('No categories/offers')
    parents={c.get('id'):c.get('parentId') for c in categories.findall('category')}
    found=set(); used=set(); dup=set()
    for offer in list(offers):
        code=(offer.findtext('vendorCode') or '').strip()
        if code in wanted:
            if code in found: dup.add(code)
            found.add(code); cid=(offer.findtext('categoryId') or '').strip();
            if cid: used.add(cid)
        else: offers.remove(offer)
    if dup: fail(f'Duplicate codes: {sorted(dup)[:20]}')
    missing=sorted(wanted-found)
    if missing: fail(f'Missing {len(missing)} Golden codes: {missing[:20]}')
    keep=set(used)
    for cid in list(used):
        pid=parents.get(cid)
        while pid: keep.add(pid); pid=parents.get(pid)
    for c in list(categories):
        if c.get('id') not in keep: categories.remove(c)
    xml=etree.tostring(root,encoding='UTF-8',xml_declaration=True,pretty_print=True)
    check=etree.fromstring(xml,parser).find('shop').find('offers').findall('offer')
    cc=[(o.findtext('vendorCode') or '').strip() for o in check]
    if len(cc)!=EXPECTED_COUNT or len(set(cc))!=EXPECTED_COUNT: fail('Final validation failed')
    meta={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'offers':len(cc),'categories':len(categories.findall('category')),'source_bytes':len(source),'output_bytes':len(xml),'sha256':hashlib.sha256(xml).hexdigest()}
    return xml,meta
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as h: h.write(data); name=h.name
    os.replace(name,path)
def main():
    codes=load_codes(); source=download(SOURCE_URL); xml,meta=build(source,codes); OUTPUT_DIR.mkdir(parents=True,exist_ok=True); atomic(OUTPUT_XML,xml)
    STATUS_JSON.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    INDEX_HTML.write_text(f'<!doctype html><html lang="uk"><meta charset="utf-8"><title>TALPA Golden 1000</title><h1>TALPA Golden 1000 Feed</h1><p>Товарів: {meta["offers"]}</p><p>Оновлено UTC: {meta["generated_at_utc"]}</p><p><a href="golden1000.xml">golden1000.xml</a></p><p><a href="status.json">status.json</a></p></html>',encoding='utf-8')
    (OUTPUT_DIR/'.nojekyll').touch(); print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
