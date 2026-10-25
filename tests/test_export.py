import datetime as dt
import unittest

from eft import export
from tests.test_forecast import record


class Export(unittest.TestCase):
    def test_dashboard_document(self):
        rec = record(quarters=40, start=dt.date(2012, 3, 31))
        last = list(rec["quarters"])[-1]
        today = (dt.date.fromisoformat(last) + dt.timedelta(days=45)).isoformat()
        doc = export.build({"T": rec}, today)
        c = doc["companies"][0]
        self.assertEqual(c["ticker"], "T")
        self.assertTrue(c["quarters"] and all(q["forecast_day"] < q["reported"] for q in c["quarters"]))
        self.assertIn(doc["chosen"]["revenue"], ("M0", "M1", "M2"))
        self.assertGreater(c["next"]["end"], last)                     # the quarter after the latest report
        self.assertIsNone(c["valuation"])                               # no cash flow in this record
        q = c["quarters"][-1]
        rf = q["revenue_forecast"][doc["chosen"]["revenue"]]
        self.assertAlmostEqual(q["revenue_surprise"], (q["revenue"] - rf) / rf)


if __name__ == "__main__":
    unittest.main()
