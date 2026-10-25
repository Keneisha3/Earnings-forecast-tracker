export const pct = (x: number | null | undefined, digits = 1) =>
  x == null || !isFinite(x) ? "–" : `${(100 * x).toFixed(digits)}%`;

export const signedPct = (x: number | null | undefined, digits = 1) =>
  x == null || !isFinite(x) ? "–" : `${x > 0 ? "+" : ""}${(100 * x).toFixed(digits)}%`;

export function money(x: number | null | undefined): string {
  if (x == null || !isFinite(x)) return "–";
  const a = Math.abs(x);
  if (a >= 1e9) return `$${(x / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `$${(x / 1e6).toFixed(1)}M`;
  return `$${x.toFixed(2)}`;
}

export const eps = (x: number | null | undefined) => (x == null || !isFinite(x) ? "–" : `$${x.toFixed(2)}`);

export const MODEL_NAMES: Record<string, string> = {
  M0: "Same quarter last year",
  M1: "Seasonal growth",
  M2: "Ridge regression",
};
