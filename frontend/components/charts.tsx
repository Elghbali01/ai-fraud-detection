import { RISK_TIERS, type RiskTier } from "@/lib/types";
import { formatNumber, percentWidth } from "@/lib/format";

const tierClass: Record<RiskTier, string> = {
  Low: "tier-low",
  Elevated: "tier-elevated",
  High: "tier-high",
  Critical: "tier-critical",
};

export function TierDistribution({ counts }: { counts: Partial<Record<RiskTier, number>> }) {
  const max = Math.max(1, ...RISK_TIERS.map((tier) => counts[tier] ?? 0));
  return (
    <div className="tier-list" aria-label="Risk tier counts from the displayed API records">
      {RISK_TIERS.map((tier) => {
        const count = counts[tier] ?? 0;
        return <div className="tier-row" key={tier}><span className="tier-name">{tier}</span><div className="progress-track" aria-hidden="true"><div className={`progress-fill ${tierClass[tier]}`} style={{ width: `${percentWidth(count, max)}%` }} /></div><span className="tier-count">{formatNumber(count, 0)}</span></div>;
      })}
    </div>
  );
}

export function HorizontalBars({ values, labelKey, valueKey }: { values: Array<Record<string, unknown>>; labelKey: string; valueKey: string }) {
  const parsed = values.map((entry) => ({ label: String(entry[labelKey] ?? "unknown"), value: Number(entry[valueKey] ?? 0) }));
  const maximum = Math.max(0, ...parsed.map((entry) => Math.abs(entry.value)));
  return <>
    <div className="chart-bars" aria-hidden="true">{parsed.map((entry, index) => <div className="chart-bar-row" key={`${entry.label}-${index}`}><span className="chart-bar-label">{entry.label}</span><div className="chart-bar-track"><div className="chart-bar-fill" style={{ width: `${percentWidth(Math.abs(entry.value), maximum)}%` }} /></div><span className="chart-bar-value">{formatNumber(entry.value, 4)}</span></div>)}</div>
    <table className="sr-only"><caption>{valueKey} values</caption><thead><tr><th scope="col">{labelKey}</th><th scope="col">{valueKey}</th></tr></thead><tbody>{parsed.map((entry, index) => <tr key={`${entry.label}-${index}`}><th scope="row">{entry.label}</th><td>{entry.value}</td></tr>)}</tbody></table>
  </>;
}

export function ShapRows({ contributions }: { contributions: Array<Record<string, unknown>> }) {
  const values = contributions.map((item) => ({
    feature: String(item.feature ?? item.name ?? item.feature_name ?? "feature"),
    value: Number(item.shap_value ?? item.contribution ?? item.value ?? item.mean_shap_value ?? 0),
  }));
  const maximum = Math.max(0, ...values.map((item) => Math.abs(item.value)));
  return <div role="list" aria-label="Feature contributions in raw log-odds space">{values.map((item, index) => {
    const width = maximum ? Math.min(50, (Math.abs(item.value) / maximum) * 50) : 0;
    return <div className="shap-row" role="listitem" key={`${item.feature}-${index}`}><span className="shap-feature">{item.feature}</span><div className="shap-track" aria-label={`${item.feature} ${item.value >= 0 ? "positive" : "negative"} log-odds contribution`}><span className="shap-zero" /><span className={`shap-bar ${item.value >= 0 ? "positive" : "negative"}`} style={{ width: `${width}%` }} /></div><span className="shap-value">{formatNumber(item.value, 5)}</span></div>;
  })}</div>;
}

export function ShapWaterfall({
  baseValue,
  outputValue,
  contributions,
}: {
  baseValue: number;
  outputValue: number;
  contributions: Array<Record<string, unknown>>;
}) {
  const rows = contributions
    .map((item) => ({
      feature: String(item.feature ?? item.name ?? item.feature_name ?? "feature"),
      value: Number(item.contribution ?? item.shap_value ?? item.value ?? 0),
    }))
    .filter((item) => Number.isFinite(item.value))
    .reduce<{ items: Array<{ feature: string; value: number; start: number; end: number }>; cumulative: number }>(
      (state, item) => {
        const row = { ...item, start: state.cumulative, end: state.cumulative + item.value };
        return { items: [...state.items, row], cumulative: row.end };
      },
      { items: [], cumulative: baseValue },
    ).items;
  const domainValues = [baseValue, outputValue, ...rows.flatMap((row) => [row.start, row.end])];
  const minimum = Math.min(...domainValues);
  const maximum = Math.max(...domainValues);
  const span = maximum - minimum || 1;
  const position = (value: number) => ((value - minimum) / span) * 100;

  return <figure className="waterfall-figure" aria-labelledby="waterfall-title">
    <div className="waterfall-head">
      <strong id="waterfall-title">Cumulative raw log-odds waterfall</strong>
      <span>Baseline {formatNumber(baseValue, 5)} → output {formatNumber(outputValue, 5)}</span>
    </div>
    <div className="waterfall-scale" aria-hidden="true"><span>{formatNumber(minimum, 4)}</span><span>{formatNumber(maximum, 4)} raw log-odds</span></div>
    <div className="waterfall-list" role="list" aria-label="Raw log-odds feature steps">
      {rows.map((row, index) => {
        const left = Math.min(position(row.start), position(row.end));
        const width = Math.max(0.7, Math.abs(position(row.end) - position(row.start)));
        return <div className="waterfall-row" role="listitem" key={`${row.feature}-${index}`}>
          <span className="waterfall-feature">{row.feature}</span>
          <span className="waterfall-track" aria-label={`${row.feature} moves raw log-odds from ${formatNumber(row.start, 5)} to ${formatNumber(row.end, 5)}`}>
            <span className={`waterfall-step ${row.value >= 0 ? "positive" : "negative"}`} style={{ left: `${left}%`, width: `${width}%` }} />
          </span>
          <span className="waterfall-value">{row.value > 0 ? "+" : ""}{formatNumber(row.value, 5)}</span>
        </div>;
      })}
    </div>
    <figcaption className="waterfall-caption">Each bar moves the cumulative raw model log-odds from its start to end. The values do not add directly to calibrated probability.</figcaption>
    <table className="sr-only">
      <caption>Raw log-odds contribution steps</caption>
      <thead><tr><th>Feature</th><th>Contribution</th><th>Starting raw log-odds</th><th>Ending raw log-odds</th></tr></thead>
      <tbody>{rows.map((row, index) => <tr key={`${row.feature}-${index}`}><th>{row.feature}</th><td>{row.value}</td><td>{row.start}</td><td>{row.end}</td></tr>)}</tbody>
      <tfoot><tr><th>Baseline</th><td colSpan={3}>{formatNumber(baseValue, 8)} raw log-odds</td></tr><tr><th>Model output</th><td colSpan={3}>{formatNumber(outputValue, 8)} raw log-odds</td></tr></tfoot>
    </table>
  </figure>;
}
