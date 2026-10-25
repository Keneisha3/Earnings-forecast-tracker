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

Walk-forward over 2507 company-quarters from 40 companies (training 1525, held out 771).

### Revenue (chosen by the rule: M1)

| model | training median error | held-out median error | held-out mean | beats M0 (held out) |
| --- | ---: | ---: | ---: | ---: |
| M0 | 7.3% (n=1525) | 7.4% (n=771) | 11.3% | - |
| M1 | 4.4% (n=1525) | 4.3% (n=771) | 9.7% | 61.9% |
| M2 | 5.0% (n=1525) | 4.5% (n=771) | 8.2% | 66.3% |

### Diluted EPS (chosen by the rule: M2)

| model | training median error | held-out median error | held-out mean | beats M0 (held out) | held-out median $ error |
| --- | ---: | ---: | ---: | ---: | ---: |
| M0 | 23.1% (n=1357) | 23.8% (n=571) | 94.5% | - | $0.440 |
| M1 | 30.5% (n=1357) | 27.3% (n=571) | 109.6% | 45.8% | $0.498 |
| M2 | 20.6% (n=1357) | 20.0% (n=571) | 104.5% | 54.7% | $0.361 |

### Held-out revenue error by sector

| sector | quarters | chosen model | M0 |
| --- | ---: | ---: | ---: |
| communication | 98 | 2.8% | 3.5% |
| consumer | 192 | 3.2% | 5.4% |
| energy | 38 | 16.6% | 12.6% |
| health | 115 | 4.9% | 6.4% |
| industrial | 97 | 6.0% | 6.0% |
| tech | 231 | 5.4% | 11.2% |
