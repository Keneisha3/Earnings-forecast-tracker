// The shape of data/dashboard.json (written by `python -m eft.export`).

export type Model = "M0" | "M1" | "M2";
export type ByModel = Partial<Record<Model, number>>;

export interface Quarter {
  end: string;
  fp: string | null;
  reported: string;
  forecast_day: string;
  revenue: number;
  revenue_forecast: ByModel;
  revenue_surprise: number | null;
  eps: number | null;
  eps_how: string | null;
  eps_forecast: ByModel;
  eps_surprise: number | null;
  revenue_tag: string | null;
}

export interface ValuationInputs {
  day: string;
  ttm_revenue: number;
  ttm_fcf: number;
  fcf_margin: number;
  growth: number;
  growth_raw: number;
  net_debt: number;
  shares: number;
}

export interface Valuation {
  inputs: ValuationInputs;
  grid: [number, number, number][];
  low: number;
  mid: number;
  high: number;
}

export interface Company {
  ticker: string;
  name: string | null;
  sector: string | null;
  cik: number | null;
  quarters: Quarter[];
  next: { end: string; revenue: ByModel; eps: ByModel } | null;
  valuation: Valuation | null;
  coverage: { quarters: number; first: string | null; have: Record<string, number> };
}

export interface ModelStats {
  train_median: number | null;
  train_n: number;
  held_median: number | null;
  held_n: number;
  held_mean: number | null;
  held_beats_m0: number | null;
  held_median_dollars?: number | null;
}

export interface Dashboard {
  built: string;
  chosen: { revenue: Model; eps: Model };
  train: [string, string];
  held_out: string;
  summary: {
    rows: number;
    companies: number;
    train_rows: number;
    held_rows: number;
    targets: Record<"revenue" | "eps", { chosen: Model; models: Record<Model, ModelStats> }>;
  };
  companies: Company[];
}
