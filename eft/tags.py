"""List the XBRL tags a company actually uses: the tool for fixing coverage gaps.

    python -m eft.tags XOM --match "Revenue|Sales"
"""

import argparse
import re
import sys

from . import sec

FORMS = ("10-Q", "10-K")


def tags(companyfacts, pattern):
    """[(taxonomy:concept, unit, facts from 10-Q/10-K, first end, last end)] matching `pattern`."""
    out = []
    rx = re.compile(pattern, re.I)
    for tax, concepts in (companyfacts.get("facts") or {}).items():
        for name, node in concepts.items():
            if not rx.search(name):
                continue
            for unit, rows in (node.get("units") or {}).items():
                rows = [r for r in rows if r.get("form") in FORMS]
                if rows:
                    ends = sorted(r["end"] for r in rows)
                    out.append(("%s:%s" % (tax, name), unit, len(rows), ends[0], ends[-1]))
    return sorted(out, key=lambda x: -x[2])


def main(argv=None):
    ap = argparse.ArgumentParser(description="List the XBRL tags a company uses.")
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--match", default="Revenue")
    ap.add_argument("--user-agent")
    ap.add_argument("--offline")
    a = ap.parse_args(argv)
    f = sec.Fetcher(a.user_agent, offline=a.offline)
    ciks = f.tickers()
    for t in a.tickers:
        print("## %s" % t)
        for row in tags(f.company_facts(ciks[t.upper()]), a.match)[:25]:
            print("%-75s %-12s %5d  %s .. %s" % row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
