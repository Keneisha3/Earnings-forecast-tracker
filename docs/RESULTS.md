# Results

## Selection rule (written 2026-10-25, before any forecast was run)

- **Targets:** next-quarter revenue and diluted EPS for each company in `eft/universe.py`.
- **Forecast date:** the day before the quarter's first filing. Inputs are only what
  `pit.as_of(that day)` returns. The forecast is scored on `pit.reported()`.
- **Eligible quarters:** the company has at least 8 earlier quarters of revenue known on the
  forecast date, and the same quarter a year earlier is known.
- **Models:**

  | Model | Revenue forecast | EPS forecast |
  | --- | --- | --- |
  | **M0 seasonal naive** (the baseline) | The same quarter last year | The same quarter last year |
  | **M1 seasonal growth** | M0 × (1 + trailing 4-quarter year-over-year growth, clipped to −50 %…+100 %) | M0 + a quarter of the change in trailing 4-quarter EPS |
  | **M2 ridge regression** | Next year-over-year log growth on its last three values, fit on the company's own history known by the forecast date (ridge λ = 1, at least 6 training points, else M1) | M0 × (M2 revenue forecast ÷ same-quarter-last-year revenue): last year's margin on the new revenue |

- **Metrics:** absolute percentage error |forecast − actual| ÷ |actual|; its median is the
  headline. EPS percentage errors are left out when |actual EPS| < $0.10, and the absolute dollar
  error is reported as well.
- **Split:** training = quarters first reported 2012-01-01 to 2021-12-31; held-out =
  2022-01-01 onwards.
- **Choice:** for each target, the model with the lowest training median error is the chosen
  model. A model other than M0 is chosen only if it beats M0's training median. The held-out
  numbers are reported once, for every model, and are never used to choose.

## Results

(filled in by `python -m eft.evaluate`, below this line)
