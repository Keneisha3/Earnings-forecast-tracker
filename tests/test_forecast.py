import copy
import datetime as dt
import unittest

from eft import evaluate, forecast as fc, pit


def record(quarters=20, growth=0.10, start=dt.date(2015, 3, 31)):
    """A company growing `growth` a year with a seasonal Q4, each quarter filed 30 days after it ends."""
    q = {}
    season = (1.0, 1.05, 1.1, 1.4)
    for i in range(quarters):
        end = (start + dt.timedelta(days=91.31 * i)).isoformat()
        filed = (dt.date.fromisoformat(end) + dt.timedelta(days=30)).isoformat()
        rev = 100.0 * (1 + growth) ** (i / 4.0) * season[i % 4]
        q[end] = {"fy": 2015 + i // 4, "fp": "Q%d" % (i % 4 + 1), "items": {
            "revenue": [[filed, rev, "reported", "Revenues"]],
            "eps_diluted": [[filed, rev / 100.0, "reported", "EarningsPerShareDiluted"]]}}
    return {"ticker": "T", "sector": "tech", "quarters": q}


class Forecasts(unittest.TestCase):
    def test_models_on_a_steadily_growing_company(self):
        rec = record()
        end = list(rec["quarters"])[-1]
        f = fc.forecast(rec, end, fc.forecast_day(rec, end))
        actual = pit.reported(rec, "revenue", end)[0]
        self.assertAlmostEqual(f["revenue"]["M0"] * 1.10, actual, delta=actual * 0.01)  # last year, no growth
        self.assertLess(abs(f["revenue"]["M1"] - actual), abs(f["revenue"]["M0"] - actual))
        self.assertLess(abs(f["revenue"]["M2"] - actual) / actual, 0.01)                # steady growth: learned
        self.assertAlmostEqual(f["eps"]["M2"] / f["eps"]["M0"], f["revenue"]["M2"] / f["revenue"]["M0"])

    def test_too_little_history_no_forecast(self):
        rec = record(quarters=8)
        end = list(rec["quarters"])[-1]
        self.assertIsNone(fc.forecast(rec, end, fc.forecast_day(rec, end)))  # 7 known: under 8

    def test_no_look_ahead(self):
        rec = record()
        ends = list(rec["quarters"])
        end = ends[14]
        day = fc.forecast_day(rec, end)
        before = fc.forecast(rec, end, day)
        wrecked = copy.deepcopy(rec)
        for e, q in wrecked["quarters"].items():
            for tl in q["items"].values():
                for v in tl:
                    if v[0] > day:
                        v[1] = v[1] * 50 - 7   # everything filed after the forecast day is garbage
                tl.append(["2099-01-01", -1e9, "reported", "x"])  # and a far-future restatement
        self.assertEqual(fc.forecast(wrecked, end, day), before)

    def test_restatement_known_by_the_day_is_used(self):
        rec = record()
        ends = list(rec["quarters"])
        end, prev = ends[16], ends[12]
        day = fc.forecast_day(rec, end)
        rec["quarters"][prev]["items"]["revenue"].append([day, 1.0, "reported", "Revenues"])  # restated, filed that day
        self.assertEqual(fc.forecast(rec, end, day)["revenue"]["M0"], 1.0)

    def test_ridge_solver(self):
        ys = [(str(i), 0.1 + 0.0 * i) for i in range(12)]
        self.assertAlmostEqual(fc.ridge_growth(ys), 0.1, places=2)
        self.assertIsNone(fc.ridge_growth(ys[:8]))  # 5 rows: under the 6 needed


class Evaluate(unittest.TestCase):
    def test_rows_split_and_rule(self):
        rs = evaluate.rows({"T": record(quarters=40, start=dt.date(2012, 3, 31))})
        self.assertTrue(all(r["forecast_day"] < r["reported"] for r in rs))
        s = evaluate.summary(rs)
        self.assertGreater(s["train_rows"], 0)
        self.assertGreater(s["held_rows"], 0)
        self.assertNotEqual(s["targets"]["revenue"]["chosen"], "M0")   # growth is learnable here
        self.assertIn("Walk-forward over", evaluate.render(s))

    def test_m0_stays_unless_beaten(self):
        flat = record(quarters=40, growth=0.0, start=dt.date(2012, 3, 31))
        s = evaluate.summary(evaluate.rows({"T": flat}))
        self.assertEqual(s["targets"]["revenue"]["chosen"], "M0")      # nothing beats a flat baseline

    def test_small_eps_uses_dollars_only(self):
        r = {"eps": 0.05, "eps_how": "reported", "eps_forecast": {"M0": 0.10}}
        self.assertEqual(evaluate.errors([r], "eps", "M0"), [])
        self.assertAlmostEqual(evaluate.dollar_errors([r], "M0")[0], 0.05)


if __name__ == "__main__":
    unittest.main()
