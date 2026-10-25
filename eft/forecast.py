"""Next-quarter revenue and EPS forecasts, from what was known on the forecast day only.

Every input comes from pit.as_of(record, item, end, day). Models (docs/RESULTS.md):
    M0 seasonal naive: the same quarter last year (the baseline every other model must beat)
    M1 seasonal growth: M0 scaled by trailing four-quarter growth (revenue) or shifted by the
       change in trailing EPS
    M2 ridge regression on the company's own year-over-year growth history (revenue); EPS keeps
       last year's margin on the M2 revenue
"""

import datetime as dt
import math

from . import pit

MODELS = ("M0", "M1", "M2")
MIN_HISTORY = 8      # quarters known before a forecast is made
MIN_TRAIN = 6        # growth observations the regression needs
RIDGE = 1.0
CLIP = (-0.5, 1.0)   # trailing growth used by M1


def _d(s):
    return dt.date.fromisoformat(s)


def history(record, item, day):
    """[(end, value)] for every quarter whose `item` was known on `day`, as known that day."""
    out = []
    for end in record["quarters"]:
        v = pit.as_of(record, item, end, day)
        if v is not None:
            out.append((end, v[0]))
    return out


def year_before(ends, end, slack=15):
    """The quarter end about a year before `end` among `ends` (52/53-week years drift by days)."""
    target = _d(end) - dt.timedelta(days=364)
    best = min(ends, key=lambda e: abs((_d(e) - target).days), default=None)
    return best if best and abs((_d(best) - target).days) <= slack else None


def _ttm_growth(hist):
    """Trailing four quarters over the four before them, minus 1 (None if not enough or not positive)."""
    if len(hist) < 8:
        return None
    a, b = sum(v for _, v in hist[-4:]), sum(v for _, v in hist[-8:-4])
    return a / b - 1 if b > 0 and a > 0 else None


def _yoy_series(hist):
    """[(end, log growth vs the same quarter a year before)] for positive values."""
    vals = dict(hist)
    ends = [e for e, _ in hist]
    out = []
    for e in ends:
        p = year_before([x for x in ends if x < e], e)
        if p and vals[e] > 0 and vals[p] > 0:
            out.append((e, math.log(vals[e] / vals[p])))
    return out


def _solve(a, b):
    """Solve a x = b (small, square) by Gaussian elimination with partial pivoting."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        if abs(m[c][c]) < 1e-12:
            return None
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def ridge_growth(yoy, lam=RIDGE):
    """Predict the next year-over-year log growth from the last three: fit y_t ~ 1 + y_{t-1} +
    y_{t-2} + y_{t-3} by ridge (the intercept is not penalized). None with too little history."""
    ys = [y for _, y in yoy]
    rows = [(ys[i - 1], ys[i - 2], ys[i - 3], ys[i]) for i in range(3, len(ys))]
    if len(rows) < MIN_TRAIN:
        return None
    k = 4
    xtx = [[0.0] * k for _ in range(k)]
    xty = [0.0] * k
    for a, b, c, y in rows:
        x = (1.0, a, b, c)
        for i in range(k):
            xty[i] += x[i] * y
            for j in range(k):
                xtx[i][j] += x[i] * x[j]
    for i in range(1, k):
        xtx[i][i] += lam
    w = _solve(xtx, xty)
    if w is None:
        return None
    return w[0] + w[1] * ys[-1] + w[2] * ys[-2] + w[3] * ys[-3]


def forecast(record, end, day):
    """{"revenue": {model: value}, "eps": {model: value}} for the quarter ending `end`, made on
    `day` from what was known then. None when the history is too short or last year's quarter
    is missing."""
    rev = history(record, "revenue", day)
    if len(rev) < MIN_HISTORY or any(e >= end for e, _ in rev):
        return None
    prev = year_before([e for e, _ in rev], end)
    if not prev:
        return None
    revd = dict(rev)
    base = revd[prev]
    out = {"revenue": {"M0": base}, "eps": {}}
    g = _ttm_growth(rev)
    out["revenue"]["M1"] = base * (1 + min(max(g, CLIP[0]), CLIP[1])) if g is not None else base
    rg = ridge_growth(_yoy_series(rev))
    out["revenue"]["M2"] = base * math.exp(rg) if rg is not None and base > 0 else out["revenue"]["M1"]
    eps = history(record, "eps_diluted", day)
    epsd = dict(eps)
    if prev in epsd:
        e0 = epsd[prev]
        out["eps"]["M0"] = e0
        recent = [v for e, v in eps if e < end]
        out["eps"]["M1"] = e0 + (sum(recent[-4:]) - sum(recent[-8:-4])) / 4.0 if len(recent) >= 8 else e0
        out["eps"]["M2"] = e0 * out["revenue"]["M2"] / base if base > 0 else e0
    return out


def forecast_day(record, end):
    """The day before the quarter's revenue was first filed: the last day a forecast was honest."""
    first = pit.reported(record, "revenue", end)
    return (_d(first[1]) - dt.timedelta(days=1)).isoformat() if first else None
