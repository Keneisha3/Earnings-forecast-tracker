"""Build the point-in-time dataset: one JSON file per company.

    python -m eft.build --out data                 # every company in eft/universe.py
    python -m eft.build --out data AAPL MSFT       # a few
    python -m eft.build --out data --offline DIR   # from saved SEC answers (tests, no network)
"""

import argparse
import json
import os
import sys

from . import pit, sec, universe


def build_all(tickers, out, fetcher, log=print):
    os.makedirs(out, exist_ok=True)
    ciks = fetcher.tickers()
    done, missing = [], []
    for t in tickers:
        cik = ciks.get(t.upper())
        if not cik:
            missing.append(t)
            log("%s: not in the SEC ticker list" % t)
            continue
        try:
            rec = pit.build(fetcher.company_facts(cik), ticker=t.upper())
        except sec.SecError as e:
            missing.append(t)
            log("%s: %s" % (t, e))
            continue
        rec["sector"] = universe.SECTOR.get(t.upper())
        with open(os.path.join(out, "%s.json" % t.upper()), "w", encoding="utf-8") as fh:
            json.dump(rec, fh, separators=(",", ":"))
        done.append(t.upper())
        log("%s: %d quarters" % (t, len(rec["quarters"])))
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"companies": done, "missing": missing}, fh, indent=1)
    return done, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description="Point-in-time company financials from SEC filings.")
    ap.add_argument("tickers", nargs="*", help="default: every company in eft/universe.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--offline", help="read saved SEC answers from this folder")
    ap.add_argument("--cache", help="save SEC answers here and reuse them")
    ap.add_argument("--user-agent", help="'Your Name you@example.com' (or set SEC_USER_AGENT)")
    a = ap.parse_args(argv)
    f = sec.Fetcher(a.user_agent, offline=a.offline, cache=a.cache)
    done, missing = build_all(a.tickers or universe.TICKERS, a.out, f, log=lambda m: print(m, file=sys.stderr))
    print("%d companies built, %d missing" % (len(done), len(missing)))
    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
