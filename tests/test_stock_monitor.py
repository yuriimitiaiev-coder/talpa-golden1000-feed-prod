"""Offline stock-monitor regression checks."""
import sys
import unittest
from pathlib import Path
from lxml import etree
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stock_monitor import build_stock_monitor


def offer(sku, available, qty):
    item = etree.Element("offer", id=sku, available="true" if available else "false")
    etree.SubElement(item, "vendorCode").text = sku
    etree.SubElement(item, "quantity_in_stock").text = str(qty)
    return item


def feed(*items):
    root = etree.Element("yml_catalog")
    holder = etree.SubElement(etree.SubElement(root, "shop"), "offers")
    holder.extend(items)
    return etree.tostring(root)


class StockMonitorTests(unittest.TestCase):
    rows = [{"sku": "A", "supplier": "SIGMA"},
            {"sku": "B", "supplier": "SIGMA"},
            {"sku": "C", "supplier": "ZAINSTRUMENTOM"}]

    def monitor(self, current, previous, **kwargs):
        return build_stock_monitor(self.rows, feed(*current), previous,
            "2026-10-12T09:00:00+00:00", sigma_feed_source=kwargs.pop("sigma_feed_source", "live"), **kwargs)

    def test_movements(self):
        old = {"A": offer("A", True, 1), "B": offer("B", False, 0), "C": offer("C", True, 9)}
        result = self.monitor([offer("A", False, 0), offer("B", True, 1), offer("C", True, 8)], old)
        self.assertEqual(result["by_supplier"]["SIGMA"]["to_unavailable"], ["A"])
        self.assertEqual(result["by_supplier"]["SIGMA"]["to_available"], ["B"])
        self.assertEqual(result["by_supplier"]["ZAINSTRUMENTOM"]["quantity_changed"], ["C"])
        self.assertEqual(result["totals"]["available"], 2)

    def test_no_baseline(self):
        result = self.monitor([offer("A", True, 1), offer("B", True, 1), offer("C", True, 8)], {})
        self.assertEqual(result["totals"]["to_available"], 0)
        self.assertEqual(result["totals"]["no_baseline"], 3)

    def test_stagnation(self):
        old = {"A": offer("A", True, 1), "B": offer("B", False, 0), "C": offer("C", True, 8)}
        history = [{"suppliers": {"SIGMA": {"unchanged_runs": 5}}}]
        result = self.monitor([offer("A", True, 1), offer("B", False, 0), offer("C", True, 8)],
                              old, history=history, history_loaded=True)
        self.assertEqual(result["by_supplier"]["SIGMA"]["unchanged_runs"], 6)
        self.assertTrue(any(x["type"] == "NO_MOVEMENT" for x in result["alerts"]))

    def test_snapshot_and_conflict(self):
        result = self.monitor([offer("A", True, 0), offer("B", True, 1), offer("C", True, 8)],
                              {}, sigma_feed_source="published_snapshot",
                              missing_supplier_skus=["B"])
        self.assertEqual(result["by_supplier"]["SIGMA"]["mismatched_quantity"], ["A"])
        self.assertTrue(any(x["type"] == "SIGMA_SNAPSHOT_FALLBACK" for x in result["alerts"]))
        self.assertEqual(result["by_supplier"]["SIGMA"]["missing_from_source"], ["B"])


if __name__ == "__main__":
    unittest.main()
