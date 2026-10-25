"""Point-in-time quarterly financials from SEC XBRL company facts.

Every number keeps every version that was filed, with its filing date, so two questions have
honest answers:

    as_of(record, item, quarter_end, day)  what a reader of the filings knew on `day`
    reported(record, item, quarter_end)    what the company first reported (the "actual")

A later filing often repeats an old quarter as a comparison, sometimes restated. The first
version is the one the market reacted to; a forecast made on a day may only use versions filed
by then. Using the latest restated value everywhere (what most tutorials do) quietly lets a
backtest see the future.

Quarters: a three-month value is used when the company reported one. Otherwise the quarter is
derived from year-to-date totals (the six-month minus the three-month, the full year minus the
nine-month: how cash flow statements and the fourth quarter usually have to be read). A derived
value is only "known" once both of its parts were filed, and its date is the later of the two.
"""

import bisect
import datetime as dt

from .items import FLOW, FORMS, ITEMS, NOT_ADDITIVE

QUARTER = (80, 100)                               # days in a quarter (13 or 14 weeks, or 3 months)
YTD = ((80, 100), (170, 195), (260, 285), (350, 380))  # quarter, half, nine months, year


def _d(s):
    return dt.date.fromisoformat(s)


def _days(start, end):
    return (_d(end) - _d(start)).days


def _within(n, band):
    return band[0] <= n <= band[1]


def concept_facts(companyfacts, concept, unit):
    """The raw facts for one us-gaap concept in one unit, from 10-Q and 10-K filings only."""
    node = (companyfacts.get("facts") or {}).get("us-gaap", {}).get(concept) or {}
    rows = (node.get("units") or {}).get(unit) or []
    return [r for r in rows if r.get("form") in FORMS and r.get("filed") and r.get("end") and "val" in r]


def period_versions(companyfacts, item):
    """{(start or None, end): [(filed, rank, value, concept, fy, fp)]} sorted by filing date, for all
    of an item's tags (rank: the tag's place in the preference list, which breaks same-day ties)."""
    statement, kind, unit, concepts = ITEMS[item]
    out = {}
    for rank, concept in enumerate(concepts):
        for r in concept_facts(companyfacts, concept, unit):
            start = r.get("start") if kind == FLOW else None
            if kind == FLOW and not start:
                continue
            key = (start, r["end"])
            out.setdefault(key, []).append((r["filed"], rank, r["val"], concept, r.get("fy"), r.get("fp")))
    for v in out.values():
        v.sort(key=lambda x: (x[0], x[1]))
        # same filing day: keep the preferred tag only
        keep, seen = [], set()
        for x in v:
            if x[0] not in seen:
                keep.append(x)
                seen.add(x[0])
        v[:] = keep
    return out


def _latest(versions, day):
    """The last version filed on or before `day`, or None."""
    i = bisect.bisect_right([x[0] for x in versions], day) - 1
    return versions[i] if i >= 0 else None


def flow_quarters(periods):
    """{quarter_end: {"direct": [(start, end)], "pairs": [((s, e_long), (s, e_short))]}}: the ways each
    quarter can be read. "pairs" are year-to-date periods sharing a start whose difference is the
    quarter (the first quarter of a year is its own year-to-date period, so it is direct)."""
    q = {}
    by_start = {}
    for (start, end) in periods:
        n = _days(start, end)
        if _within(n, QUARTER):
            q.setdefault(end, {"direct": [], "pairs": []})["direct"].append((start, end))
        if any(_within(n, b) for b in YTD):
            by_start.setdefault(start, []).append(end)
    for start, ends in by_start.items():
        ends = sorted(set(ends))
        for short, long_ in zip(ends, ends[1:]):
            if _within(_days(short, long_), QUARTER):
                q.setdefault(long_, {"direct": [], "pairs": []})["pairs"].append(((start, long_), (start, short)))
    return q


def flow_timeline(periods, ways, approx=False):
    """[[filed, value, how, concept]] each time what was known about one quarter changed. how:
    "reported" (a three-month value), "derived" (a difference of year-to-date values) or "approx"
    (derived for a value that does not add up, like EPS)."""
    dates = set()
    for key in ways["direct"]:
        dates.update(x[0] for x in periods[key])
    for long_, short in ways["pairs"]:
        dates.update(x[0] for x in periods[long_])
        dates.update(x[0] for x in periods[short])
    out = []
    for day in sorted(dates):
        best = None
        for key in ways["direct"]:
            v = _latest(periods[key], day)
            if v and (best is None or v[0] > best[0]):
                best = (v[0], v[2], "reported", v[3])
        if best is None:  # a three-month value always wins once one is out
            for long_, short in ways["pairs"]:
                a, b = _latest(periods[long_], day), _latest(periods[short], day)
                if a and b:
                    cand = (max(a[0], b[0]), a[2] - b[2], "approx" if approx else "derived", a[3])
                    if best is None or cand[0] > best[0]:
                        best = cand
        if best and (not out or out[-1][1:] != [best[1], best[2], best[3]]):
            out.append([day, best[1], best[2], best[3]])
    return out


def _fiscal_label(periods, ways):
    """(fy, fp) as the first filing that covered the quarter labelled it (a derived quarter that ends
    a year is Q4)."""
    firsts = [periods[k][0] for k in ways["direct"]] + [periods[l][0] for l, _ in ways["pairs"]]
    if not firsts:
        return None, None
    f = min(firsts, key=lambda x: x[0])
    fp = f[5]
    if ways["pairs"] and not ways["direct"] and fp == "FY":
        fp = "Q4"
    return f[4], fp


def build(companyfacts, ticker=None):
    """One company's point-in-time record:
    {"ticker", "cik", "name", "quarters": {end: {"fy", "fp", "items": {item: timeline}}}}
    where each timeline is [[filed, value, how, concept], ...] (see flow_timeline)."""
    quarters = {}
    for item, (statement, kind, unit, concepts) in ITEMS.items():
        periods = period_versions(companyfacts, item)
        if kind == FLOW:
            for end, ways in flow_quarters(periods).items():
                tl = flow_timeline(periods, ways, approx=item in NOT_ADDITIVE)
                if not tl:
                    continue
                qd = quarters.setdefault(end, {"fy": None, "fp": None, "items": {}})
                qd["items"][item] = tl
                if item == "revenue" or qd["fy"] is None:
                    fy, fp = _fiscal_label(periods, ways)
                    if fy is not None:
                        qd["fy"], qd["fp"] = fy, fp
        else:
            for (_, end), versions in periods.items():
                tl = []
                for filed, rank, val, concept, fy, fp in versions:
                    if not tl or tl[-1][1] != val:
                        tl.append([filed, val, "reported", concept])
                quarters.setdefault(end, {"fy": None, "fp": None, "items": {}})["items"][item] = tl
    # keep only quarter ends that have a flow item: balance sheets also report odd dates
    quarters = {e: q for e, q in quarters.items()
                if any(ITEMS[i][1] == FLOW for i in q["items"])}
    return {"ticker": ticker, "cik": companyfacts.get("cik"), "name": companyfacts.get("entityName"),
            "quarters": dict(sorted(quarters.items()))}


def as_of(record, item, end, day):
    """What was known on `day` about `item` for the quarter ending `end`: (value, filed, how) or None."""
    tl = ((record["quarters"].get(end) or {}).get("items") or {}).get(item)
    if not tl:
        return None
    v = _latest(tl, day)
    return (v[1], v[0], v[2]) if v else None


def reported(record, item, end):
    """What the company first reported: (value, filed, how) or None. The actual a forecast is scored on."""
    tl = ((record["quarters"].get(end) or {}).get("items") or {}).get(item)
    return (tl[0][1], tl[0][0], tl[0][2]) if tl else None


def known_quarters(record, item, day):
    """Quarter ends whose `item` had been filed by `day`, oldest first."""
    return [e for e, q in record["quarters"].items()
            if (q["items"].get(item) or [[None]])[0][0] is not None and q["items"][item][0][0] <= day]


def free_cash_flow(record, end, day=None):
    """Operating cash flow minus capital spending for a quarter, as known on `day` (None: as reported)."""
    get = (lambda i: as_of(record, i, end, day)) if day else (lambda i: reported(record, i, end))
    a, b = get("operating_cash_flow"), get("capex")
    return a[0] - b[0] if a and b else None
