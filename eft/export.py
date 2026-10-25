"""One compact file for the dashboard: data/dashboard.json.

    python -m eft.export --data data [--today YYYY-MM-DD]

Per company: every forecast quarter (reported, each model's forecast, the surprise against the
chosen model, the tag and filing date behind the actual), the forecast for the next quarter made
today, the DCF range today, and coverage. Plus the walk-forward summary.
"""

import argparse
import datetime as dt
import json
import os
import sys

from . import coverage, evaluate, forecast as fc, pit, valuation


def next_quarter(rec, today):
    """The forecast for the quarter after the latest reported one, made `today`:
    {"end" (estimated: a year after the quarter it is compared with), "revenue": {...}, "eps": {...}}."""
    ends = pit.known_quarters(rec, "revenue", today)
    if len(ends) < 4:
        return None
    end = (dt.date.fromisoformat(ends[-4]) + dt.timedelta(days=364)).isoformat()
    f = fc.forecast(rec, end, today)
    return dict(f, end=end) if f else None


def company(t, rec, rows, chosen, today):
    qs = []
    for r in rows:
        rf, ef = r["revenue_forecast"][chosen["revenue"]], r["eps_forecast"].get(chosen["eps"])
        tag = pit.as_of(rec, "revenue", r["end"], r["reported"])
        qs.append({"end": r["end"], "fp": r["fp"], "reported": r["reported"], "forecast_day": r["forecast_day"],
                   "revenue": r["revenue"], "revenue_forecast": r["revenue_forecast"],
                   "revenue_surprise": (r["revenue"] - rf) / abs(rf) if rf else None,
                   "eps": r["eps"], "eps_how": r["eps_how"], "eps_forecast": r["eps_forecast"],
                   "eps_surprise": (r["eps"] - ef) / abs(ef) if ef and r["eps"] is not None and abs(ef) >= 0.10
                   else None,
                   "revenue_tag": (rec["quarters"][r["end"]]["items"]["revenue"][0][3]) if tag else None})
    return {"ticker": t, "name": rec.get("name"), "sector": rec.get("sector"), "cik": rec.get("cik"),
            "quarters": qs, "next": next_quarter(rec, today), "valuation": valuation.value(rec, today),
            "coverage": coverage.company(rec)}


def build(records, today):
    rs = evaluate.rows(records)
    s = evaluate.summary(rs)
    chosen = {k: v["chosen"] for k, v in s["targets"].items()}
    by = {}
    for r in rs:
        by.setdefault(r["ticker"], []).append(r)
    return {"built": today, "summary": s, "chosen": chosen, "train": evaluate.TRAIN, "held_out": evaluate.HELD_OUT,
            "companies": [company(t, rec, by.get(t, []), chosen, today) for t, rec in sorted(records.items())]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export the dashboard data.")
    ap.add_argument("--data", required=True)
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--out", help="default: DATA/dashboard.json")
    a = ap.parse_args(argv)
    doc = build(evaluate.load(a.data), a.today)
    out = a.out or os.path.join(a.data, "dashboard.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    print("%s: %d companies, %.0f KB" % (out, len(doc["companies"]), os.path.getsize(out) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
