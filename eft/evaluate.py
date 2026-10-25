"""Walk-forward test of the forecasts, under the rule in docs/RESULTS.md.

    python -m eft.evaluate --data data            # writes data/forecasts.json and prints the tables
    python -m eft.evaluate --data data --write-results docs/RESULTS.md

For every company-quarter with enough history: forecast on the day before the first report,
score against the first report. Training = reported 2012-2021, held out = 2022 on.
"""

import argparse
import json
import os
import statistics
import sys

from . import forecast as fc
from . import pit

TRAIN = ("2012-01-01", "2021-12-31")
HELD_OUT = "2022-01-01"
EPS_FLOOR = 0.10  # |EPS| under this: percentage error is meaningless, dollars only
MARK = "(filled in by `python -m eft.evaluate`, below this line)"


def load(folder):
    with open(os.path.join(folder, "index.json"), encoding="utf-8") as fh:
        names = json.load(fh)["companies"]
    out = {}
    for t in names:
        with open(os.path.join(folder, "%s.json" % t), encoding="utf-8") as fh:
            out[t] = json.load(fh)
    return out


def rows(records):
    """One row per company-quarter forecast: ticker, sector, end, day, reported, actuals, forecasts."""
    out = []
    for t, rec in sorted(records.items()):
        for end in rec["quarters"]:
            day = fc.forecast_day(rec, end)
            if not day:
                continue
            f = fc.forecast(rec, end, day)
            if not f:
                continue
            rev = pit.reported(rec, "revenue", end)
            eps = pit.reported(rec, "eps_diluted", end)
            out.append({"ticker": t, "sector": rec.get("sector"), "end": end, "forecast_day": day,
                        "reported": rev[1], "fp": rec["quarters"][end].get("fp"),
                        "revenue": rev[0], "revenue_how": rev[2], "revenue_forecast": f["revenue"],
                        "eps": eps[0] if eps else None, "eps_how": eps[2] if eps else None,
                        "eps_forecast": f["eps"]})
    return out


def ape(f, a):
    return abs(f - a) / abs(a) if a else None


def errors(rs, target, model):
    """Absolute percentage errors (as fractions) for one target and model over rows `rs`."""
    out = []
    for r in rs:
        if target == "revenue":
            if r["revenue"] and r["revenue"] > 0:
                out.append(ape(r["revenue_forecast"][model], r["revenue"]))
        else:
            a = r["eps"]
            if a is not None and r["eps_how"] != "approx" and abs(a) >= EPS_FLOOR and model in r["eps_forecast"]:
                out.append(ape(r["eps_forecast"][model], a))
    return [e for e in out if e is not None]


def dollar_errors(rs, model):
    return [abs(r["eps_forecast"][model] - r["eps"]) for r in rs
            if r["eps"] is not None and r["eps_how"] != "approx" and model in r["eps_forecast"]]


def split(rs):
    train = [r for r in rs if TRAIN[0] <= r["reported"] <= TRAIN[1]]
    held = [r for r in rs if r["reported"] >= HELD_OUT]
    return train, held


def beats(rs, target, model, base="M0"):
    """Share of quarters where `model` was closer than the baseline."""
    pairs = []
    for r in rs:
        if target == "revenue":
            if r["revenue"]:
                pairs.append((abs(r["revenue_forecast"][model] - r["revenue"]),
                              abs(r["revenue_forecast"][base] - r["revenue"])))
        elif r["eps"] is not None and r["eps_how"] != "approx" and model in r["eps_forecast"]:
            pairs.append((abs(r["eps_forecast"][model] - r["eps"]), abs(r["eps_forecast"][base] - r["eps"])))
    return sum(a < b for a, b in pairs) / len(pairs) if pairs else None


def choose(train, target):
    """The rule: the lowest training median error; a model other than M0 only if it beats M0's."""
    med = {m: statistics.median(errors(train, target, m)) for m in fc.MODELS if errors(train, target, m)}
    best = min(med, key=med.get)
    return best if med[best] < med.get("M0", float("inf")) else "M0"


def summary(rs):
    train, held = split(rs)
    out = {"rows": len(rs), "train_rows": len(train), "held_rows": len(held),
           "companies": len({r["ticker"] for r in rs}), "targets": {}}
    for target in ("revenue", "eps"):
        t = {"chosen": choose(train, target), "models": {}}
        for m in fc.MODELS:
            et, eh = errors(train, target, m), errors(held, target, m)
            t["models"][m] = {
                "train_median": statistics.median(et) if et else None, "train_n": len(et),
                "held_median": statistics.median(eh) if eh else None, "held_n": len(eh),
                "held_mean": statistics.mean(eh) if eh else None,
                "held_beats_m0": beats(held, target, m) if m != "M0" else None}
            if target == "eps":
                d = dollar_errors(held, m)
                t["models"][m]["held_median_dollars"] = statistics.median(d) if d else None
        out["targets"][target] = t
    by_sector = {}
    for r in held:
        by_sector.setdefault(r["sector"], []).append(r)
    ch = out["targets"]["revenue"]["chosen"]
    out["held_by_sector"] = {s: {"n": len(v), "chosen": statistics.median(errors(v, "revenue", ch)),
                                 "M0": statistics.median(errors(v, "revenue", "M0"))}
                             for s, v in sorted(by_sector.items()) if errors(v, "revenue", ch)}
    return out


def _p(x):
    return "-" if x is None else "%.1f%%" % (100 * x)


def render(s):
    L = ["Walk-forward over %d company-quarters from %d companies (training %d, held out %d)." % (
        s["rows"], s["companies"], s["train_rows"], s["held_rows"]), ""]
    for target, label in (("revenue", "Revenue"), ("eps", "Diluted EPS")):
        t = s["targets"][target]
        L += ["### %s (chosen by the rule: %s)" % (label, t["chosen"]), "",
              "| model | training median error | held-out median error | held-out mean | beats M0 (held out) |"
              + (" held-out median $ error |" if target == "eps" else ""),
              "| --- | ---: | ---: | ---: | ---: |" + (" ---: |" if target == "eps" else "")]
        for m, v in t["models"].items():
            L.append("| %s | %s (n=%d) | %s (n=%d) | %s | %s |%s" % (
                m, _p(v["train_median"]), v["train_n"], _p(v["held_median"]), v["held_n"], _p(v["held_mean"]),
                _p(v["held_beats_m0"]) if v["held_beats_m0"] is not None else "-",
                (" $%.3f |" % v["held_median_dollars"]) if target == "eps" and v.get("held_median_dollars") is not None
                else (" - |" if target == "eps" else "")))
        L.append("")
    L += ["### Held-out revenue error by sector", "", "| sector | quarters | chosen model | M0 |", "| --- | ---: | ---: | ---: |"]
    for sec, v in s["held_by_sector"].items():
        L.append("| %s | %d | %s | %s |" % (sec, v["n"], _p(v["chosen"]), _p(v["M0"])))
    return "\n".join(L) + "\n"


def write_results(path, text):
    with open(path, encoding="utf-8") as fh:
        doc = fh.read()
    head = doc.split(MARK)[0] + MARK
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(head + "\n\n" + text)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Walk-forward test of the revenue and EPS forecasts.")
    ap.add_argument("--data", required=True)
    ap.add_argument("--write-results", help="replace the results section of this markdown file")
    a = ap.parse_args(argv)
    rs = rows(load(a.data))
    if not rs:
        print("no forecasts: is the data built?", file=sys.stderr)
        return 1
    s = summary(rs)
    with open(os.path.join(a.data, "forecasts.json"), "w", encoding="utf-8") as fh:
        json.dump({"summary": s, "rows": rs}, fh, separators=(",", ":"))
    text = render(s)
    print(text)
    if a.write_results:
        write_results(a.write_results, text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
