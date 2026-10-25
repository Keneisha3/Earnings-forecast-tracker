import copy
import datetime as dt
import unittest

from eft import live
from tests.test_forecast import record


class Live(unittest.TestCase):
    def test_freeze_then_score_only_later_reports(self):
        full = record(quarters=40, start=dt.date(2012, 3, 31))
        ends = list(full["quarters"])
        past = copy.deepcopy(full)
        del past["quarters"][ends[-1]]                      # the last quarter is not reported yet
        today = (dt.date.fromisoformat(ends[-2]) + dt.timedelta(days=40)).isoformat()
        frozen = live.freeze({"T": past}, today, {"revenue": "M1", "eps": "M2"})
        f = frozen["forecasts"]["T"]
        self.assertLessEqual(abs((dt.date.fromisoformat(f["end"]) - dt.date.fromisoformat(ends[-1])).days), 15)
        rows = live.score(frozen, {"T": full})                # later, the company reported it
        self.assertEqual([r["end"] for r in rows], [ends[-1]])
        self.assertEqual(rows[0]["revenue_forecast"], f["revenue"])
        self.assertEqual(live.score(frozen, {"T": past}), [])  # nothing reported after the freeze yet


if __name__ == "__main__":
    unittest.main()
