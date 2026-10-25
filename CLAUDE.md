# Earnings Forecast Tracker: notes for Claude

A public portfolio project: point-in-time SEC financials, walk-forward revenue/EPS forecasts,
a DCF range, and a React dashboard. See docs/PRODUCT.md (scope) and docs/PLAN.md (phases).

## Rules that always hold

- **Point in time.** A forecast for a quarter may only read `pit.as_of(record, item, end, day)`
  for a day before that quarter's first report. Scores use `pit.reported()`. A test corrupts
  everything filed after the forecast day and checks the forecast does not change; keep it.
- **Never call anything "consensus".** Consensus data is paid. Compare against our baselines.
- **Report honestly.** Pick models on the training years only (rule in docs/RESULTS.md, written
  before the results); report the held-out years once. If a model does not beat the seasonal
  naive baseline, say so.
- **No personal data.** The SEC User-Agent is passed through the SEC_USER_AGENT secret or a
  masked workflow input, never written to files.

## Code

- Python 3.10+, standard library only for `eft/` (no numpy: the regression is small and solved
  in closed form). Pure functions for the math, thin CLIs, offline tests (`tests/`, fixtures built
  in code).
- `python -m unittest discover -s tests -t .` must pass before every push.
