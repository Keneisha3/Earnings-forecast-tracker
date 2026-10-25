# Earnings Forecast Tracker

Company financials from SEC filings, kept **point in time**: every number keeps each version that
was filed, so you can ask both "what did the company first report?" and "what was known on this
day?". On top of that, next-quarter revenue and EPS forecasts, tested walk-forward against what
companies actually reported, and a simple DCF valuation range.

- **Why point in time matters:** companies restate, and later filings repeat old quarters with
  new numbers. A backtest that uses the latest numbers everywhere quietly sees the future. Here
  every forecast is built from filings available before its quarter's report.
- **What it is not:** analyst consensus. Consensus data is paid. Forecasts are compared with
  transparent baselines, starting with the same quarter last year.

Status: phase 1 (the data layer) is done. See [docs/PLAN.md](docs/PLAN.md) for the rest and
[docs/PRODUCT.md](docs/PRODUCT.md) for who it is for and what was left out.

## Use

Python 3.10+, standard library only for the data layer.

```bash
export SEC_USER_AGENT="Your Name you@example.com"   # SEC requires it
python -m eft.build --out data --cache cache AAPL MSFT
python -m unittest discover -s tests -t .
```

```python
import json
from eft import pit

rec = json.load(open("data/AAPL.json"))
pit.reported(rec, "revenue", "2024-12-28")                   # (value, filed, "reported" | "derived")
pit.as_of(rec, "revenue", "2024-12-28", day="2025-01-15")    # None: not filed yet
```

The `data` workflow builds all 40 companies weekly on GitHub and publishes them to the `data`
branch.

## How quarters are built

- A three-month value is used when the company reported one.
- Otherwise the quarter is the difference of year-to-date totals. The full year minus nine
  months gives the fourth quarter; six months minus three gives a cash-flow second quarter.
  A derived value counts as known only once both parts were filed.
- Derived EPS is marked approximate, because share counts change within a year.
- Companies tag the same item differently. Each standardized item tries its tags in order
  (`eft/items.py`), and the tag used is kept with the value.

## Credits

The XBRL approach (concept lists and the fourth-quarter derivation) started from the earnings
reader in [Jakeschincariol/trader-skill](https://github.com/Jakeschincariol/trader-skill) (MIT),
by way of my [public-stock-trade-tracker](https://github.com/Keneisha3/public-stock-trade-tracker).
The point-in-time versioning is new here. Data: SEC EDGAR XBRL company facts.
