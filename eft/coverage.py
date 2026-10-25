"""Coverage: which standardized items exist for each company-quarter, and sanity checks.

    python -m eft.coverage --data data            # prints the report
    python -m eft.coverage --data data --out docs/COVERAGE.md

Checks, on first-reported values: gross profit = revenue - cost of revenue (within 1 %), and
assets >= liabilities (equity can be negative, so only the sign of the gap is checked).
"""

import argparse
import datetime as dt
import sys

from . import evaluate, pit
from .items import HELPERS, ITEMS

SINCE = "2012-01-01"


def _gaps(ends):
    """Quarter ends more than ~4 months after the previous one (a missing quarter between)."""
    out = []
    for a, b in zip(ends, ends[1:]):
        if (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days > 125:
            out.append((a, b))
    return out


def company(rec, since=SINCE):
    ends = [e for e in rec["quarters"] if e >= since and pit.reported(rec, "revenue", e)]
    have = {i: sum(1 for e in ends if pit.reported(rec, i, e)) for i in ITEMS if i not in HELPERS}
    gp_bad = 0
    for e in ends:
        r, c, g = (pit.reported(rec, i, e) for i in ("revenue", "cost_of_revenue", "gross_profit"))
        if r and c and g and abs((r[0] - c[0]) - g[0]) > 0.01 * abs(r[0]):
            gp_bad += 1
    return {"quarters": len(ends), "first": ends[0] if ends else None, "last": ends[-1] if ends else None,
            "have": have, "gaps": _gaps(ends), "gross_profit_mismatch": gp_bad}


def report(records):
    rows = {t: company(r) for t, r in sorted(records.items())}
    items = [i for i in ITEMS if i not in HELPERS]
    L = ["# Coverage", "", "Company-quarters since %s with reported revenue, and the share of them with each item." % SINCE, "",
         "| company | quarters | first | gaps | " + " | ".join(items) + " |",
         "| --- | ---: | --- | ---: | " + " | ".join("---:" for _ in items) + " |"]
    for t, c in rows.items():
        n = c["quarters"] or 1
        L.append("| %s | %d | %s | %d | %s |" % (t, c["quarters"], c["first"], len(c["gaps"]),
                                                 " | ".join("%.0f%%" % (100.0 * c["have"][i] / n) for i in items)))
    tot = sum(c["quarters"] for c in rows.values()) or 1
    L += ["", "**All companies:** " + ", ".join("%s %.0f%%" % (i, 100.0 * sum(c["have"][i] for c in rows.values()) / tot)
                                               for i in items), ""]
    gaps = [(t, a, b) for t, c in rows.items() for a, b in c["gaps"]]
    if gaps:
        L += ["**Missing quarters** (more than four months between two reported quarters):", ""]
        L += ["- %s: between %s and %s" % g for g in gaps]
    bad = {t: c["gross_profit_mismatch"] for t, c in rows.items() if c["gross_profit_mismatch"]}
    if bad:
        L += ["", "**Gross profit not equal to revenue - cost of revenue** (quarters): " +
              ", ".join("%s %d" % kv for kv in bad.items())]
    return "\n".join(L) + "\n", rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="Coverage of the standardized items.")
    ap.add_argument("--data", required=True)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    text, _ = report(evaluate.load(a.data))
    print(text)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
