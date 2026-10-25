import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Company, Dashboard, Model, Quarter } from "./types";
import { eps, money, MODEL_NAMES, pct, signedPct } from "./format";
import { fairValue } from "./valuation";

export default function App() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ticker, setTicker] = useState<string>(() => new URLSearchParams(location.search).get("t") || "AAPL");

  useEffect(() => {
    fetch("dashboard.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`dashboard.json: HTTP ${r.status}`))))
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    const u = new URL(location.href);
    u.searchParams.set("t", ticker);
    history.replaceState(null, "", u);
  }, [ticker]);

  if (error) return <main className="wrap"><p className="error">Could not load the data: {error}</p></main>;
  if (!data) return <main className="wrap"><p className="muted">Loading…</p></main>;

  const company = data.companies.find((c) => c.ticker === ticker) ?? data.companies[0];
  return (
    <main className="wrap">
      <header>
        <h1>Earnings Forecast Tracker</h1>
        <p className="muted">
          Next-quarter revenue and EPS forecasts from SEC filings, tested walk-forward against what companies first
          reported. Data built {data.built}.
        </p>
      </header>
      <Scorecard data={data} />
      <Picker companies={data.companies} value={company.ticker} onChange={setTicker} />
      <CompanyView key={company.ticker} c={company} chosen={data.chosen} heldOut={data.held_out} />
      <footer className="muted">
        Forecasts use only filings available the day before each report, and are scored on the first reported
        number. They are compared with simple baselines, not analyst consensus (consensus data is licensed).
        Not investment advice. Method: <a href="https://github.com/Keneisha3/earnings-forecast-tracker">source and docs</a>.
      </footer>
    </main>
  );
}

function Scorecard({ data }: { data: Dashboard }) {
  const t = data.summary.targets;
  const card = (label: string, target: "revenue" | "eps") => {
    const ch = t[target].chosen;
    const m = t[target].models;
    return (
      <div className="card stat">
        <div className="label">{label}: median error, held-out years ({data.held_out.slice(0, 4)} on)</div>
        <div className="big">{pct(m[ch].held_median)}</div>
        <div className="muted">
          {MODEL_NAMES[ch]} ({ch}) vs {pct(m.M0.held_median)} for same-quarter-last-year · closer in{" "}
          {pct(m[ch].held_beats_m0, 0)} of {m[ch].held_n} quarters
        </div>
      </div>
    );
  };
  return (
    <section className="grid3">
      {card("Revenue", "revenue")}
      {card("Diluted EPS", "eps")}
      <div className="card stat">
        <div className="label">Tested on</div>
        <div className="big">{data.summary.rows.toLocaleString()}</div>
        <div className="muted">
          company-quarters from {data.summary.companies} companies; models chosen on {data.train[0].slice(0, 4)}–
          {data.train[1].slice(0, 4)} only
        </div>
      </div>
    </section>
  );
}

function Picker({ companies, value, onChange }: { companies: Company[]; value: string; onChange: (t: string) => void }) {
  const sectors = useMemo(() => {
    const m = new Map<string, Company[]>();
    companies.forEach((c) => m.set(c.sector ?? "other", [...(m.get(c.sector ?? "other") ?? []), c]));
    return [...m.entries()];
  }, [companies]);
  return (
    <section className="picker">
      <label>
        Company{" "}
        <select value={value} onChange={(e) => onChange(e.target.value)}>
          {sectors.map(([s, cs]) => (
            <optgroup key={s} label={s}>
              {cs.map((c) => (
                <option key={c.ticker} value={c.ticker}>
                  {c.ticker} · {c.name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
    </section>
  );
}

function CompanyView({ c, chosen, heldOut }: { c: Company; chosen: { revenue: Model; eps: Model }; heldOut: string }) {
  const recent = c.quarters.slice(-24);
  const chart = recent.map((q) => ({
    end: q.end.slice(0, 7),
    Reported: q.revenue / 1e9,
    Forecast: (q.revenue_forecast[chosen.revenue] ?? NaN) / 1e9,
    "Last year": (q.revenue_forecast.M0 ?? NaN) / 1e9,
  }));
  const held = c.quarters.filter((q) => q.reported >= heldOut);
  const err = (qs: Quarter[], m: Model) => {
    const e = qs.map((q) => Math.abs((q.revenue_forecast[m] ?? NaN) - q.revenue) / Math.abs(q.revenue)).filter(isFinite);
    e.sort((a, b) => a - b);
    return e.length ? e[Math.floor(e.length / 2)] : null;
  };
  return (
    <>
      <section className="card">
        <div className="title-row">
          <h2>
            {c.name} <span className="muted">({c.ticker} · {c.sector})</span>
          </h2>
          {c.cik != null && (
            <a href={`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${c.cik}&type=10-Q`} target="_blank" rel="noreferrer">
              SEC filings ↗
            </a>
          )}
        </div>
        <p className="muted">
          This company, held-out years: median revenue error {pct(err(held, chosen.revenue))} (chosen model) vs{" "}
          {pct(err(held, "M0"))} (same quarter last year), {held.length} quarters.
        </p>
        {c.next && <NextQuarter c={c} chosen={chosen} />}
      </section>

      <section className="card">
        <h3>Revenue: reported vs forecast ($ billions)</h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chart} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
            <XAxis dataKey="end" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} width={48} />
            <Tooltip formatter={(v: number) => `$${v.toFixed(2)}B`} />
            <Legend />
            <Line type="monotone" dataKey="Reported" stroke="var(--c1)" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="Forecast" stroke="var(--c2)" strokeWidth={2} strokeDasharray="5 3" dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="Last year" stroke="var(--c3)" strokeWidth={1} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </section>

      <QuarterTable qs={c.quarters.slice(-12).reverse()} chosen={chosen} />
      <div className="grid2">
        <ValuationCard c={c} />
        <Coverage c={c} />
      </div>
    </>
  );
}

function NextQuarter({ c, chosen }: { c: Company; chosen: { revenue: Model; eps: Model } }) {
  const n = c.next!;
  return (
    <div className="next">
      <div>
        <div className="label">Next quarter (ending about {n.end})</div>
        <div className="big">{money(n.revenue[chosen.revenue])}</div>
        <div className="muted">revenue forecast · last year {money(n.revenue.M0)}</div>
      </div>
      <div>
        <div className="label">&nbsp;</div>
        <div className="big">{eps(n.eps[chosen.eps])}</div>
        <div className="muted">diluted EPS forecast · last year {eps(n.eps.M0)}</div>
      </div>
    </div>
  );
}

function QuarterTable({ qs, chosen }: { qs: Quarter[]; chosen: { revenue: Model; eps: Model } }) {
  const cls = (x: number | null) => (x == null ? "" : x > 0 ? "pos" : x < 0 ? "neg" : "");
  return (
    <section className="card">
      <h3>Last 12 quarters</h3>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>Quarter</th>
              <th>Reported</th>
              <th className="num">Revenue</th>
              <th className="num">Forecast</th>
              <th className="num">Surprise</th>
              <th className="num">EPS</th>
              <th className="num">Forecast</th>
              <th className="num">Surprise</th>
            </tr>
          </thead>
          <tbody>
            {qs.map((q) => (
              <tr key={q.end}>
                <td title={q.revenue_tag ?? ""}>
                  {q.end} <span className="muted">{q.fp}</span>
                </td>
                <td>{q.reported}</td>
                <td className="num">{money(q.revenue)}</td>
                <td className="num">{money(q.revenue_forecast[chosen.revenue])}</td>
                <td className={`num ${cls(q.revenue_surprise)}`}>{signedPct(q.revenue_surprise)}</td>
                <td className="num" title={q.eps_how === "approx" ? "derived from year-to-date totals: approximate" : ""}>
                  {eps(q.eps)}
                  {q.eps_how === "approx" ? "*" : ""}
                </td>
                <td className="num">{eps(q.eps_forecast[chosen.eps])}</td>
                <td className={`num ${cls(q.eps_surprise)}`}>{signedPct(q.eps_surprise)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">
        Surprise = (reported − forecast) ÷ forecast, against the chosen model. Forecasts were made the day before each
        report. * EPS derived from year-to-date totals (approximate). Hover a quarter for the XBRL tag.
      </p>
    </section>
  );
}

function ValuationCard({ c }: { c: Company }) {
  const v = c.valuation;
  const [growth, setGrowth] = useState(v?.inputs.growth ?? 0);
  const [margin, setMargin] = useState(v?.inputs.fcf_margin ?? 0);
  const [rate, setRate] = useState(0.09);
  const [terminal, setTerminal] = useState(0.025);
  if (!v) {
    return (
      <section className="card">
        <h3>Valuation</h3>
        <p className="muted">No DCF: free cash flow is negative or not reported, and a DCF on it says nothing.</p>
      </section>
    );
  }
  const value = fairValue(v.inputs, rate, terminal, growth, margin);
  const slider = (label: string, val: number, set: (x: number) => void, min: number, max: number, step: number) => (
    <label className="slider">
      <span>
        {label} <b>{pct(val)}</b>
      </span>
      <input type="range" min={min} max={max} step={step} value={val} onChange={(e) => set(Number(e.target.value))} />
    </label>
  );
  return (
    <section className="card">
      <h3>Valuation (DCF on free cash flow)</h3>
      <div className="big">${value.toFixed(2)} <span className="muted small">per share</span></div>
      <p className="muted small">
        Range over the default grid: ${v.low.toFixed(2)} to ${v.high.toFixed(2)} (discount 8–11 %, terminal growth
        1.5–3 %). Trailing FCF {money(v.inputs.ttm_fcf)} on revenue {money(v.inputs.ttm_revenue)}, net debt{" "}
        {money(v.inputs.net_debt)}.
      </p>
      {slider("Revenue growth, year 1", growth, setGrowth, -0.1, 0.3, 0.005)}
      {slider("FCF margin", margin, setMargin, 0, 0.6, 0.005)}
      {slider("Discount rate", rate, setRate, 0.06, 0.14, 0.0025)}
      {slider("Terminal growth", terminal, setTerminal, 0, 0.04, 0.0025)}
      <p className="muted small">Compare with the current share price yourself. A model output, not an opinion on the stock.</p>
    </section>
  );
}

const ITEM_LABELS: Record<string, string> = {
  revenue: "Revenue", cost_of_revenue: "Cost of revenue", gross_profit: "Gross profit",
  operating_income: "Operating income", net_income: "Net income", eps_diluted: "Diluted EPS",
  shares_diluted: "Diluted shares", cash: "Cash", total_assets: "Total assets",
  total_liabilities: "Total liabilities", equity: "Equity", long_term_debt: "Long-term debt",
  operating_cash_flow: "Operating cash flow", capex: "Capital spending",
};

function Coverage({ c }: { c: Company }) {
  const n = c.coverage.quarters || 1;
  return (
    <section className="card">
      <h3>Coverage since 2012</h3>
      <p className="muted small">
        {c.coverage.quarters} quarters with revenue, first {c.coverage.first}. Share of them with each standardized item:
      </p>
      <ul className="cov">
        {Object.entries(c.coverage.have).map(([k, v]) => (
          <li key={k}>
            <span>{ITEM_LABELS[k] ?? k}</span>
            <span className="bar"><i style={{ width: `${(100 * v) / n}%` }} /></span>
            <span className="num">{pct(v / n, 0)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
