// The same DCF as eft/valuation.py, so the sliders recompute in the browser.
import type { ValuationInputs } from "./types";

export const YEARS = 5;

export function fairValue(inp: ValuationInputs, rate: number, terminal: number, growth: number, margin: number): number {
  let rev = inp.ttm_revenue;
  let pv = 0;
  for (let year = 1; year <= YEARS; year++) {
    const g = growth + ((terminal - growth) * (year - 1)) / (YEARS - 1);
    rev *= 1 + g;
    pv += (rev * margin) / (1 + rate) ** year;
  }
  const tv = (rev * margin * (1 + terminal)) / (rate - terminal);
  const ev = pv + tv / (1 + rate) ** YEARS;
  return (ev - inp.net_debt) / inp.shares;
}
