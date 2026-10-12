"""Offline tests for TALPA human-readable stock report."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stock_dashboard import render_dashboard


def sample():
    return {
        "schema_version": 1,
        "generated_at_utc": "2026-10-12T10:28:02+00:00",
        "totals": {"active": 3, "available": 2, "unavailable": 1,
                   "to_available": 0, "to_unavailable": 1, "quantity_changed": 1},
        "by_supplier": {
            "SIGMA": {"active": 2, "available": 2, "unavailable": 0,
                      "to_available": [], "to_unavailable": [], "quantity_changed": [],
                      "missing_from_source": [], "mismatched_quantity": [],
                      "unchanged_runs": 6},
            "ZAINSTRUMENTOM": {"active": 1, "available": 0, "unavailable": 1,
                      "to_available": [], "to_unavailable": ["1101-1704"],
                      "quantity_changed": ["1101-1704"],
                      "missing_from_source": [], "mismatched_quantity": [],
                      "unchanged_runs": 0},
        },
        "alerts": [{"type": "NO_MOVEMENT", "supplier": "SIGMA", "runs": 6}],
        "history": [{"generated_at_utc": "2026-10-12T10:28:02+00:00",
                     "suppliers": {
                         "SIGMA": {"available": 2, "unavailable": 0, "to_available": 0,
                                   "to_unavailable": 0, "quantity_changed": 0},
                         "ZAINSTRUMENTOM": {"available": 0, "unavailable": 1, "to_available": 0,
                                           "to_unavailable": 1, "quantity_changed": 1},
                     }}],
    }


class DashboardTests(unittest.TestCase):
    def test_dashboard_renders_all_sections_and_real_counts(self):
        html = render_dashboard(sample())
        for expected in ("TALPA — Контроль наявності", "Постачальники",
                         "Артикули, що потребують уваги", "Історія оновлень",
                         "1101-1704", "Заінструментом", "Потрібна увага", "6/6",
                         "12.10.2026 о 13:28", 'href="stock_monitor.json"'):
            self.assertIn(expected, html)
        self.assertIn('<div class="v">3</div>', html)
        self.assertIn('<div class="v accent">2</div>', html)

    def test_escapes_untrusted_sku_and_alert_text(self):
        report = sample()
        report["by_supplier"]["ZAINSTRUMENTOM"]["to_unavailable"] = [
            '<script>alert("x")</script>'
        ]
        html = render_dashboard(report)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_empty_history_and_no_active_supplier(self):
        report = sample()
        report["alerts"] = []
        report["history"] = []
        report["by_supplier"]["SIGMA"]["unchanged_runs"] = 0
        html = render_dashboard(report)
        self.assertIn("Історія ще не накопичена", html)
        self.assertIn("Критичних сигналів моніторингу немає", html)

    def test_rejects_inconsistent_totals(self):
        report = sample()
        report["totals"]["available"] = 3
        with self.assertRaises(ValueError):
            render_dashboard(report)


if __name__ == "__main__":
    unittest.main()
