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

**Dashboard:** https://keneisha3.github.io/Earnings-forecast-tracker/ · **Product brief:**
[docs/PRODUCT.md](docs/PRODUCT.md) · **Plan:** [docs/PLAN.md](docs/PLAN.md)

## Results

Walk-forward over 2,507 company-quarters from 40 companies, 2012-2026. Each forecast uses only
filings available the day before the quarter's report, and is scored on the first reported
number. Models were chosen on 2012-2021 by a rule written before any results
([docs/RESULTS.md](docs/RESULTS.md)). The numbers below are the held-out years, 2022 onwards:

| Target | Chosen model | Median error | Baseline (same quarter last year) | Closer than the baseline |
| --- | --- | ---: | ---: | ---: |
| Revenue | Seasonal growth | **4.3 %** | 7.4 % | 62 % of 771 quarters |
| Diluted EPS | Last year's margin on the forecast revenue | **20.0 %** ($0.36) | 23.8 % ($0.44) | 55 % of 571 quarters |

Where it does **not** work:
- **Energy.** Chevron and ConocoPhillips: 16.6 % against 12.6 % for the baseline. Oil prices
  turn, and extrapolating last year's growth makes it worse.
- **Industrials.** No better than the baseline (6.0 % both).
- **EPS.** Mean errors stay large because one-off charges and gains swamp any model built
  on history.

The regression (M2) has the lowest held-out *mean* revenue error (8.2 %). It was not chosen,
because the rule picks on the training median, and it is reported as is.

Data fixes made after the first run touched coverage only, never the models:
- 16- and 17-week quarters (Costco, PepsiCo).
- Derived gross profit and total liabilities.
- More capex and debt tags.
- ConocoPhillips in place of ExxonMobil, whose SEC company facts start in 2025.

[docs/COVERAGE.md](docs/COVERAGE.md) has the item-by-item coverage per company.

### Live test

On 2026-10-25, before any of them reported, the next-quarter forecasts for all 40 companies were
frozen in [live/2026-10-25.json](live/2026-10-25.json). The git commit date proves they came
first. After earnings season, `python -m eft.live score live/2026-10-25.json --data data` scores
them on what the companies reported.

## Use

Python 3.10+, standard library only for the data layer.

```bash
export SEC_USER_AGENT="Your Name you@example.com"   # SEC requires it
python -m eft.build --out data --cache cache AAPL MSFT
python -m eft.coverage --data data          # what is missing and why
python -m eft.evaluate --data data          # the walk-forward test
python -m eft.export --data data            # data/dashboard.json for the dashboard
python -m unittest discover -s tests -t .
cd web && npm ci && cp ../data/dashboard.json public/ && npm run dev
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
