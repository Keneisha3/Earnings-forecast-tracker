import datetime as dt
import unittest

from eft import valuation


def record(n=8, cfo=30.0, capex=10.0):
    q = {}
    for i in range(n):
        end = (dt.date(2022, 3, 31) + dt.timedelta(days=91.31 * i)).isoformat()
        filed = (dt.date.fromisoformat(end) + dt.timedelta(days=30)).isoformat()
        item = lambda v: [[filed, v, "reported", "x"]]  # noqa: E731
        q[end] = {"items": {"revenue": item(100.0), "operating_cash_flow": item(cfo), "capex": item(capex),
                            "shares_diluted": item(10.0), "long_term_debt": item(50.0), "cash": item(30.0)}}
    return {"quarters": q}


class Valuation(unittest.TestCase):
    def test_inputs_and_grid(self):
        rec = record()
        day = "2030-01-01"
        inp = valuation.inputs(rec, day)
        self.assertEqual((inp["ttm_revenue"], inp["ttm_fcf"], inp["net_debt"], inp["shares"]), (400.0, 80.0, 20.0, 10.0))
        self.assertAlmostEqual(inp["fcf_margin"], 0.2)
        v = valuation.value(rec, day)
        self.assertEqual(len(v["grid"]), len(valuation.RATES) * len(valuation.TERMINAL))
        self.assertLess(v["low"], v["mid"])
        self.assertLess(v["mid"], v["high"])
        # higher discount rate, lower value
        self.assertGreater(valuation.fair_value(inp, 0.08, 0.025), valuation.fair_value(inp, 0.11, 0.025))
        # flat revenue at 2.5% terminal growth: check one value by hand
        rev, pv = 400.0, 0.0
        for y in range(1, 6):
            rev *= 1 + 0.025 * (y - 1) / 4
            pv += rev * 0.2 / 1.09 ** y
        tv = rev * 0.2 * 1.025 / (0.09 - 0.025) / 1.09 ** 5
        self.assertAlmostEqual(v["mid"], round((pv + tv - 20) / 10, 2))

    def test_point_in_time_and_negative_fcf(self):
        rec = record()
        first_of_last = list(rec["quarters"].values())[-1]["items"]["revenue"][0][0]
        self.assertIsNone(valuation.inputs(rec, (dt.date.fromisoformat(first_of_last) - dt.timedelta(days=1)).isoformat()))
        self.assertIsNone(valuation.value(record(capex=40.0), "2030-01-01"))  # burning cash: no DCF


if __name__ == "__main__":
    unittest.main()
