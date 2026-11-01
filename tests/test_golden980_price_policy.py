"""Regression tests: TALPA Golden980 uses supplier RRP; historic rollback stays intact."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lxml import etree
from pool_builder import effective_selling_price

def supplier_offer(price):
    node=etree.Element("offer")
    etree.SubElement(node,"price").text=str(price)
    return node

class Golden980PricePolicy(unittest.TestCase):
    def test_grand_supplier_price_changes_in_golden980(self):
        row={"sku":"BFC4000","supplier":"GRANDINSTRUMENT","fallback_price":"1100"}
        with patch.dict(os.environ,{"GOLDEN980_MODE":"1"}):
            self.assertEqual(effective_selling_price(supplier_offer("1247"),row),"1247")
            self.assertEqual(effective_selling_price(supplier_offer("1251"),row),"1251")
    def test_grand_legacy_price_unchanged(self):
        row={"sku":"BFC4000","supplier":"GRANDINSTRUMENT","fallback_price":"1100"}
        with patch.dict(os.environ,{"GOLDEN980_MODE":"0"}):
            self.assertEqual(effective_selling_price(supplier_offer("1247"),row),"1100")
    def test_sigma_live_price(self):
        row={"sku":"4003021","supplier":"SIGMA","fallback_price":"1000"}
        with patch.dict(os.environ,{"GOLDEN980_MODE":"1"}):
            self.assertEqual(effective_selling_price(supplier_offer("999"),row),"999")
    def test_za_live_rrp(self):
        row={"sku":"9001","supplier":"ZAINSTRUMENTOM","fallback_price":"1000"}
        with patch.dict(os.environ,{"GOLDEN980_MODE":"1"}):
            self.assertEqual(effective_selling_price(supplier_offer("950"),row),"950")
if __name__=="__main__":
    unittest.main()
