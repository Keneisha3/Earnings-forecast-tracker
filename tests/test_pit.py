import json
import os
import shutil
import tempfile
import unittest

from eft import build, pit, sec


def fact(start, end, val, filed, form="10-Q", fy=2023, fp="Q1"):
    f = {"end": end, "val": val, "filed": filed, "form": form, "fy": fy, "fp": fp, "accn": filed + form}
    if start:
        f["start"] = start
    return f


def company():
    """A calendar-year company's 2023 as it was filed, then a restatement in 2024."""
    old_rev = [  # 2023 used the old revenue tag
        fact("2023-01-01", "2023-03-31", 100, "2023-05-01"),
        fact("2023-04-01", "2023-06-30", 110, "2023-08-01", fp="Q2"),
        fact("2023-01-01", "2023-06-30", 210, "2023-08-01", fp="Q2"),
        fact("2023-07-01", "2023-09-30", 120, "2023-11-01", fp="Q3"),
        fact("2023-01-01", "2023-09-30", 330, "2023-11-01", fp="Q3"),
        fact("2023-07-01", "2023-09-30", 999, "2023-10-25", form="8-K"),  # a press release: not a 10-Q
    ]
    new_rev = [  # the 10-K switched tags; Q1 2024's 10-Q restated Q1 2023 as a comparison
        fact("2023-01-01", "2023-12-31", 460, "2024-02-15", form="10-K", fp="FY"),
        fact("2023-01-01", "2023-03-31", 105, "2024-05-01", fy=2024),
    ]
    cfo = [  # cash flow: year to date only
        fact("2023-01-01", "2023-03-31", 50, "2023-05-01"),
        fact("2023-01-01", "2023-06-30", 90, "2023-08-01", fp="Q2"),
        fact("2023-01-01", "2023-09-30", 150, "2023-11-01", fp="Q3"),
        fact("2023-01-01", "2023-12-31", 200, "2024-02-15", form="10-K", fp="FY"),
    ]
    capex = [fact("2023-01-01", "2023-03-31", 20, "2023-05-01"),
             fact("2023-01-01", "2023-06-30", 35, "2023-08-01", fp="Q2")]
    eps = [fact("2023-01-01", "2023-03-31", 1.00, "2023-05-01"),
           fact("2023-04-01", "2023-06-30", 1.10, "2023-08-01", fp="Q2"),
           fact("2023-07-01", "2023-09-30", 1.20, "2023-11-01", fp="Q3"),
           fact("2023-01-01", "2023-09-30", 3.30, "2023-11-01", fp="Q3"),
           fact("2023-01-01", "2023-12-31", 4.70, "2024-02-15", form="10-K", fp="FY")]
    assets = [fact(None, "2023-03-31", 1000, "2023-05-01"), fact(None, "2023-03-31", 1000, "2024-05-01")]
    g = {"SalesRevenueNet": {"units": {"USD": old_rev}},
         "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": new_rev}},
         "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": cfo}},
         "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": capex}},
         "EarningsPerShareDiluted": {"units": {"USD/shares": eps}},
         "Assets": {"units": {"USD": assets}}}
    return {"cik": 1234, "entityName": "Example Co", "facts": {"us-gaap": g}}


class PointInTime(unittest.TestCase):
    def setUp(self):
        self.rec = pit.build(company(), "EXM")

    def test_actual_is_the_first_report_and_restatements_wait_for_their_filing(self):
        self.assertEqual(pit.reported(self.rec, "revenue", "2023-03-31"), (100, "2023-05-01", "reported"))
        self.assertIsNone(pit.as_of(self.rec, "revenue", "2023-03-31", "2023-04-30"))  # not filed yet
        self.assertEqual(pit.as_of(self.rec, "revenue", "2023-03-31", "2024-04-30")[0], 100)
        self.assertEqual(pit.as_of(self.rec, "revenue", "2023-03-31", "2024-05-01")[0], 105)  # restated

    def test_press_releases_are_ignored(self):
        self.assertEqual(pit.reported(self.rec, "revenue", "2023-09-30")[0], 120)

    def test_fourth_quarter_is_derived_when_the_10k_is_filed(self):
        self.assertIsNone(pit.as_of(self.rec, "revenue", "2023-12-31", "2024-02-14"))
        self.assertEqual(pit.as_of(self.rec, "revenue", "2023-12-31", "2024-02-15"), (130, "2024-02-15", "derived"))
        q4 = self.rec["quarters"]["2023-12-31"]
        self.assertEqual((q4["fy"], q4["fp"]), (2023, "Q4"))

    def test_cash_flow_from_year_to_date_totals(self):
        self.assertEqual(pit.reported(self.rec, "operating_cash_flow", "2023-06-30"), (40, "2023-08-01", "derived"))
        self.assertIsNone(pit.as_of(self.rec, "operating_cash_flow", "2023-06-30", "2023-07-31"))
        self.assertEqual(pit.reported(self.rec, "operating_cash_flow", "2023-12-31")[0], 50)
        self.assertEqual(pit.free_cash_flow(self.rec, "2023-03-31"), 30)
        self.assertEqual(pit.free_cash_flow(self.rec, "2023-06-30"), 25)   # (90-50) - (35-20)

    def test_eps_derived_from_totals_is_marked_approximate(self):
        v = pit.reported(self.rec, "eps_diluted", "2023-12-31")
        self.assertAlmostEqual(v[0], 1.40)
        self.assertEqual(v[2], "approx")

    def test_balance_sheet_and_known_quarters(self):
        self.assertEqual(pit.reported(self.rec, "total_assets", "2023-03-31")[0], 1000)
        self.assertEqual(len(self.rec["quarters"]["2023-03-31"]["items"]["total_assets"]), 1)  # same value twice
        self.assertEqual(pit.known_quarters(self.rec, "revenue", "2023-11-01"),
                         ["2023-03-31", "2023-06-30", "2023-09-30"])

    def test_tag_used_is_kept(self):
        tl = self.rec["quarters"]["2023-03-31"]["items"]["revenue"]
        self.assertEqual([x[3] for x in tl], ["SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"])


class Build(unittest.TestCase):
    def test_offline_build_writes_one_file_per_company(self):
        src, out = tempfile.mkdtemp(), tempfile.mkdtemp()
        try:
            with open(os.path.join(src, "company_tickers.json"), "w") as fh:
                json.dump({"0": {"cik_str": 1234, "ticker": "EXM", "title": "Example Co"}}, fh)
            with open(os.path.join(src, "CIK0000001234.json"), "w") as fh:
                json.dump(company(), fh)
            done, missing = build.build_all(["EXM", "NOPE"], out, sec.Fetcher(offline=src), log=lambda m: None)
            self.assertEqual((done, missing), (["EXM"], ["NOPE"]))
            with open(os.path.join(out, "EXM.json")) as fh:
                rec = json.load(fh)
            self.assertEqual(pit.reported(rec, "revenue", "2023-12-31")[0], 130)
        finally:
            shutil.rmtree(src)
            shutil.rmtree(out)

    def test_no_user_agent_no_request(self):
        with self.assertRaisesRegex(sec.SecError, "User-Agent"):
            sec.Fetcher(user_agent="").get_json(sec.TICKERS_URL)


if __name__ == "__main__":
    unittest.main()
