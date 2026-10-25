"""A plain DCF on free cash flow, as a range, from what was known on a day.

Inputs (all from pit.as_of on `day`):
    trailing-twelve-month revenue and free cash flow (operating cash flow - capex), so the FCF margin
    revenue growth: trailing four quarters over the four before, clipped to -10 %..+30 %
    net debt: long-term debt - cash, from the latest balance sheet; shares: latest diluted count
Projection: five years of revenue, the growth fading in a straight line to the terminal rate, at the
trailing FCF margin; a Gordon terminal value; discounted at each rate in the grid. Fair value per
share for every (discount rate, terminal growth) pair. Not an opinion on any stock.
"""

from . import pit

RATES = (0.08, 0.09, 0.10, 0.11)
TERMINAL = (0.015, 0.025, 0.03)
GROWTH_CLIP = (-0.10, 0.30)
YEARS = 5


def _last(rec, item, day, n):
    """The last `n` quarters' values of `item` known on `day`, oldest first (None if fewer)."""
    vals = []
    for end in rec["quarters"]:
        v = pit.as_of(rec, item, end, day)
        if v is not None:
            vals.append((end, v[0]))
    return [v for _, v in vals[-n:]] if len(vals) >= n else None


def _latest(rec, item, day):
    for end in reversed(list(rec["quarters"])):
        v = pit.as_of(rec, item, end, day)
        if v is not None:
            return v[0]
    return None


def inputs(rec, day):
    rev8 = _last(rec, "revenue", day, 8)
    cfo, capex = _last(rec, "operating_cash_flow", day, 4), _last(rec, "capex", day, 4)
    shares = _latest(rec, "shares_diluted", day)
    if not rev8 or not cfo or not capex or not shares:
        return None
    ttm_rev, prev_rev = sum(rev8[-4:]), sum(rev8[:4])
    fcf = sum(cfo) - sum(capex)
    growth = ttm_rev / prev_rev - 1 if prev_rev > 0 else 0.0
    debt = _latest(rec, "long_term_debt", day) or 0.0
    cash = _latest(rec, "cash", day) or 0.0
    return {"day": day, "ttm_revenue": ttm_rev, "ttm_fcf": fcf, "fcf_margin": fcf / ttm_rev if ttm_rev else None,
            "growth": min(max(growth, GROWTH_CLIP[0]), GROWTH_CLIP[1]), "growth_raw": growth,
            "net_debt": debt - cash, "shares": shares}


def fair_value(inp, rate, terminal, growth=None, margin=None):
    """Fair value per share for one discount rate and terminal growth (growth and margin can be
    overridden: the dashboard's sliders)."""
    g0 = inp["growth"] if growth is None else growth
    m = inp["fcf_margin"] if margin is None else margin
    rev, pv = inp["ttm_revenue"], 0.0
    for year in range(1, YEARS + 1):
        g = g0 + (terminal - g0) * (year - 1) / (YEARS - 1)
        rev *= 1 + g
        pv += rev * m / (1 + rate) ** year
    tv = rev * m * (1 + terminal) / (rate - terminal)
    ev = pv + tv / (1 + rate) ** YEARS
    return (ev - inp["net_debt"]) / inp["shares"]


def value(rec, day):
    """{"inputs", "grid": [[rate, terminal, per share]], "low", "mid", "high"} or None (missing data,
    or negative free cash flow: a DCF on it says nothing)."""
    inp = inputs(rec, day)
    if not inp or inp["ttm_fcf"] <= 0:
        return None
    grid = [[r, t, round(fair_value(inp, r, t), 2)] for r in RATES for t in TERMINAL]
    vals = sorted(v for _, _, v in grid)
    return {"inputs": inp, "grid": grid, "low": vals[0], "mid": round(fair_value(inp, 0.09, 0.025), 2),
            "high": vals[-1]}
