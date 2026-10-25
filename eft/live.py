"""Live test: freeze next-quarter forecasts before companies report, score them after.

    python -m eft.live freeze --data data --out live/2026-10-25.json
    python -m eft.live score live/2026-10-25.json --data data

A frozen file is committed to git the day it is made, so its forecasts provably came before the
results: the one test a backtest cannot fake. Scoring matches each forecast to the quarter the
company then reported (its end within 15 days of the estimated end, first filed after the freeze).
"""

import argparse
import datetime as dt
import json
import os
import statistics
import sys

from . import evaluate, export, pit


def freeze(records, today, chosen):
    out = {}
    for t, rec in sorted(records.items()):
        n = export.next_quarter(rec, today)
        if n:
            out[t] = {"end": n["end"], "revenue": n["revenue"], "eps": n["eps"]}
    return {"frozen_on": today, "chosen": chosen, "forecasts": out}


def score(frozen, records):
    rows = []
    for t, f in frozen["forecasts"].items():
        rec = records.get(t)
        if not rec:
            continue
        target = dt.date.fromisoformat(f["end"])
        for end in rec["quarters"]:
            if abs((dt.date.fromisoformat(end) - target).days) > 15:
                continue
            rev, eps = pit.reported(rec, "revenue", end), pit.reported(rec, "eps_diluted", end)
            if rev and rev[1] > frozen["frozen_on"]:
                rows.append({"ticker": t, "end": end, "reported": rev[1], "revenue": rev[0],
                             "revenue_forecast": f["revenue"], "eps": eps[0] if eps else None,
                             "eps_how": eps[2] if eps else None, "eps_forecast": f["eps"]})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="Freeze live forecasts, or score a frozen file.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    fz = sub.add_parser("freeze")
    fz.add_argument("--data", required=True)
    fz.add_argument("--out", required=True)
    fz.add_argument("--today", default=dt.date.today().isoformat())
    sc = sub.add_parser("score")
    sc.add_argument("file")
    sc.add_argument("--data", required=True)
    a = ap.parse_args(argv)
    records = evaluate.load(a.data)
    if a.cmd == "freeze":
        chosen = {k: v["chosen"] for k, v in evaluate.summary(evaluate.rows(records))["targets"].items()}
        doc = freeze(records, a.today, chosen)
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        print("froze %d forecasts on %s -> %s" % (len(doc["forecasts"]), a.today, a.out))
        return 0
    with open(a.file, encoding="utf-8") as fh:
        frozen = json.load(fh)
    rows = score(frozen, records)
    print("%d of %d frozen forecasts have been reported since %s" % (len(rows), len(frozen["forecasts"]),
                                                                     frozen["frozen_on"]))
    for target in ("revenue", "eps"):
        for m in sorted({"M0", frozen["chosen"][target]}):
            e = evaluate.errors(rows, target, m)
            if e:
                print("  %s %s: median error %.1f%% over %d" % (target, m, 100 * statistics.median(e), len(e)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
