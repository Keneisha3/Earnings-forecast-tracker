# Build plan

Each phase ends with something that runs and is tested. Phases 1 to 3 are the core: the
measured forecast error comes out of phase 3.

## Phase 1: point-in-time data (done)

- `eft/sec.py`: SEC client. It requires a User-Agent, stays under SEC's rate limit, retries, and
  has an offline mode and a cache.
- `eft/items.py`: 14 standardized items across the income statement, balance sheet and cash
  flow, each with its XBRL tags in order of preference.
- `eft/pit.py`: every filed version of every number. Quarters come from three-month values, or
  are derived from year-to-date totals. Exposes `as_of(day)` and `reported()`.
- `eft/build.py`: one JSON file per company. The `data` GitHub workflow builds it weekly and
  publishes it to the `data` branch.
- Tests: tag switch, restatement, derived fourth quarter, cash flow reported only year to date,
  approximate EPS, an 8-K that is ignored, and offline build.

## Phase 2: coverage report (done)

- Build all 40 companies. For each company-quarter, record which items are present and which
  tag was used.
- A `coverage.md` lists the gaps with their cause: a missing tag, an unusual fiscal calendar,
  or a restatement. Each common cause gets fixed by adding a tag or a rule, with a test, until
  coverage is above 95 % for the income statement.
- Sanity checks: gross profit = revenue − cost of revenue where all three exist, and assets ≈
  liabilities + equity. Each disagreement is logged.

## Phase 3: forecasts and the walk-forward test (done)

Forecast next-quarter revenue and EPS with these models:

| Model | Forecast |
| --- | --- |
| Seasonal naive (the baseline) | The same quarter last year |
| Seasonal growth | The same quarter last year × the trailing 4-quarter year-over-year growth |
| Regression | Ridge regression of next year-over-year log growth on its last three values, fit per company on what was known by the forecast date; falls back to seasonal growth when history is short. For EPS: last year's margin on the forecast revenue. |

- **Walk-forward.** For each company and quarter Q, the forecast date is the day before Q's
  first report. Every input comes from `pit.as_of(that day)`, and the score is
  `pit.reported(Q)`.
- **Look-ahead test.** Corrupt every value filed after the forecast date. The forecast must not
  change. The same idea is already used in the stock-tracker replay.
- **Metrics.** Median and mean absolute percentage error, the share of quarters that beat the
  baseline, and the error by sector and by year. EPS errors are measured in dollars as well as
  percent, because percent blows up near zero.
- **Pick on training years only.** Choose the model on 2012–2021, then report 2022–2026 once.
  Write the selection rule down before looking.

## Phase 4: valuation (done)

- A three-stage DCF on free cash flow: trailing twelve months, years 1–5 at a growth rate that
  fades to a terminal rate, and the terminal value.
- Inputs default from the data (trailing growth, FCF margin) and are all adjustable.
- A range: a grid of discount rates (8–11 %) × terminal growth rates (1.5–3 %), shown as fair
  value per share (compare it with the price yourself: prices are not part of this data).
- Net debt and the diluted share count are taken from the latest balance sheet as of the date.

## Phase 5: React dashboard (done)

- Vite + React + TypeScript and a charting library. It reads the published JSON, with no backend.
- Views:
  - **Company:** the quarter table (reported, forecast, surprise %) and the error over time.
  - **Valuation:** the range with assumption sliders.
  - **Coverage:** what is missing and why.
- Each quarter shows its XBRL tag on hover; the company links to its SEC filings.
- Deployed to GitHub Pages after every data build and every push to main.

## Phase 6: live season (next)

- Freeze the forecasts for every company due to report next season, before they report, and
  timestamp the frozen file in git.
- Score them after the season. This is the number the backtest cannot fake.

## Not in scope (see PRODUCT.md)

Consensus estimates, banks and insurers, segment KPIs, machine-learning models, and intraday
prices.
