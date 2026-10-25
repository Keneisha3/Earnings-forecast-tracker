# Earnings Forecast Tracker: product brief

## The user

An equity analyst who covers 15 to 40 companies and updates a model for each one every
quarter. Earnings season compresses that work into a few weeks: most of the companies report
within the same month, often several on the same evening.

## The problem

After a company reports, the analyst needs three answers fast:

1. **What changed?** The new quarter, standardized so it compares with prior quarters and peers.
2. **Was it a surprise?** Reported results against what was expected.
3. **Does the valuation move?** A fair-value range that updates with the new numbers.

Today that means opening the 10-Q, retyping numbers into a spreadsheet, and lining up line items
that each company labels differently. The retyping is slow and error-prone. The standardizing is
where the judgment is, and it is redone by hand every quarter.

## What this builds

A small web tool covering 40 large US companies across six sectors:

- **Standardized financials from SEC filings.** Income statement, balance sheet and cash-flow
  items mapped from each company's own XBRL tags into one schema. The tag used is kept, so every
  number traces back to its filing.
- **Point-in-time history.** Every figure keeps each version filed, with its date: what was first
  reported, and what was known on any given day. The forecasts depend on this.
- **A next-quarter forecast** of revenue and EPS for each company, from deliberately plain models:
  a seasonal baseline and a regression on the company's own history.
- **An honest test.** Forecasts run walk-forward. Each one uses only filings available before
  that quarter's report, and is scored against what the company first reported. That gives a
  measured error, not a claimed one.
- **A valuation view.** A simple DCF with the key assumptions visible and adjustable (growth,
  margin, discount rate), shown as a range rather than one number.
- **A dashboard.** Pick a company and see reported against forecast for each quarter, the surprise,
  forecast error over time, and the valuation range.

## What it leaves out, on purpose

| Left out | Why |
| --- | --- |
| Analyst consensus estimates | Consensus data is paid and licensed. The tracker compares against its own transparent baselines and never presents its forecast as "consensus". |
| Banks and insurers | Their revenue (net interest income, premiums) is not comparable, and their models are different. |
| Intraday prices and trading signals | This is a fundamentals tool. Market prices enter only as an input to the valuation. |
| Segment and KPI data (iPhone units, same-store sales) | Valuable, but not standardized in XBRL. A good next step, too large for version 1. |
| Machine-learning models | Simple models with honest walk-forward errors are easier to trust and to explain. A complex model must beat them on the same test to earn its place. |

## How success is measured

- **Forecast accuracy:** the median absolute percentage error of next-quarter revenue and EPS
  across all companies and quarters in the walk-forward test. It has to beat the seasonal-naive
  baseline (same quarter last year) on the same quarters to count.
- **Coverage:** the share of company-quarters with a complete standardized income statement,
  balance sheet and cash flow. Every gap is logged with its reason.
- **Time to answer:** after a filing, the new quarter, the surprise and the updated valuation are on
  the dashboard after the next data build, with no retyping.
- **Traceability:** every number on screen links to its tag and filing date.

## Risks

- **Restatements and tag changes.** Handled by keeping every version and the tag behind each
  number. The tests cover a tag switch and a restatement.
- **Fourth quarters and cash flows that exist only year to date.** Derived as differences of
  year-to-date totals, and dated to when both parts were filed. Derived EPS is marked approximate,
  because share counts change during a year.
- **Look-ahead in the test.** Ruled out by building every forecast from data available as of its
  date only, and testing that rule directly.
