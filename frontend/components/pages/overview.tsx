"use client";

import Link from "next/link";
import { useApi } from "@/lib/use-api";
import { formatDate, formatNumber, formatProbability } from "@/lib/format";
import type { Analysis, Investigation, PageResponse, Prediction, RiskTier } from "@/lib/types";
import { Card, CardHeading, EmptyState, ErrorState, MetricCard, PageHeader, RiskBadge, SectionHeading } from "@/components/ui";
import { TierDistribution } from "@/components/charts";

const historyPath = "/history?limit=100&offset=0&sort_order=desc";

export function OverviewPage() {
  const history = useApi<PageResponse<Prediction>>(historyPath);
  const analyses = useApi<PageResponse<Analysis>>("/analyses?limit=100&offset=0");
  const investigations = useApi<PageResponse<Investigation>>("/investigations?limit=100&offset=0&status=Open");
  const records = history.data?.results ?? [];
  const tierCounts = records.reduce<Partial<Record<RiskTier, number>>>((counts, row) => {
    counts[row.risk_tier] = (counts[row.risk_tier] ?? 0) + 1;
    return counts;
  }, {});
  const flagged = records.filter((row) => row.predicted_class === 1).length;
  const elevatedOrHigher = records.filter((row) => row.risk_tier !== "Low").length;
  const completed = (analyses.data?.analyses ?? []).filter((item) => item.status === "completed").length;
  const recentAnalyses = (analyses.data?.analyses ?? []).slice(0, 5);

  return <>
    <PageHeader eyebrow="Command center / overview" title="Fraud intelligence" description="A bounded view of predictions and analyst work persisted by the local Mission 04 API. Model outputs support triage; they do not establish fraud ground truth." actions={<Link className="button button-primary" href="/predict">Open prediction lab <span aria-hidden="true">↗</span></Link>} />
    {(history.error || analyses.error) ? <div className="stack-sm" style={{ marginBottom: 16 }}>{history.error ? <ErrorState error={history.error} onRetry={history.refresh} /> : null}{analyses.error ? <ErrorState error={analyses.error} onRetry={analyses.refresh} /> : null}</div> : null}

    <div className="grid grid-4" aria-label="API-backed summary">
      <MetricCard label="Predictions stored" value={history.data ? formatNumber(history.data.total ?? 0, 0) : history.loading ? "…" : "—"} note="All persisted history records" icon="transactions" />
      <MetricCard label="Flagged for review" value={history.data ? formatNumber(flagged, 0) : history.loading ? "…" : "—"} note={`Within latest ${records.length} fetched rows`} icon="risk" />
      <MetricCard label="Elevated risk or higher" value={history.data ? formatNumber(elevatedOrHigher, 0) : history.loading ? "…" : "—"} note={`Within latest ${records.length} fetched rows`} icon="chart" />
      <MetricCard label="Open investigations" value={investigations.data ? formatNumber(investigations.data.count, 0) : investigations.loading ? "…" : "—"} note="Current API page · maximum 100" icon="investigations" />
    </div>

    <div className="grid grid-main-side" style={{ marginTop: 15 }}>
      <Card className="card-pad">
        <CardHeading title="Risk tier mix" description="Operational review categories from the latest fetched history page." action={<span className="badge">{records.length} RECORDS</span>} />
        {history.error ? <p className="card-copy">Risk distribution is unavailable because the history request failed.</p> : history.loading ? <div className="loading-surface"><div className="skeleton medium" /><div className="skeleton" /><div className="skeleton" /><div className="skeleton short" /></div> : records.length ? <TierDistribution counts={tierCounts} /> : <EmptyState icon="chart" title="No predictions to summarize" description="The API has no persisted history yet. Run a prediction or analyze a feature-only CSV to begin." action={<Link className="button button-default" href="/predict">Start a review</Link>} />}
        <div className="footer-note">Risk tiers come from the persisted Mission 03 policy. Threshold categories are not calibrated probability bands.</div>
      </Card>

      <Card className="card-pad">
        <CardHeading title="Analysis activity" description="Most recent saved CSV jobs returned by the API." action={<Link className="table-action" href="/csv">View all</Link>} />
        {analyses.error ? <p className="card-copy">Analysis history is unavailable. Retry after the API is ready.</p> : analyses.loading ? <div className="loading-surface"><div className="skeleton medium" /><div className="skeleton" /><div className="skeleton" /></div> : recentAnalyses.length ? <div className="stack-sm">{recentAnalyses.map((analysis) => <Link className="analysis-card" href={`/analyses/${analysis.analysis_id}`} key={analysis.analysis_id}><div><h3>{formatNumber(analysis.processed_rows, 0)} / {formatNumber(analysis.requested_rows, 0)} rows processed</h3><p>{formatDate(analysis.created_at)}</p><div className="analysis-card-meta"><span className="badge tone-neutral">{analysis.status}</span>{analysis.model_version ? <span className="badge">{analysis.model_version}</span> : null}</div></div><span className="button button-quiet" aria-hidden="true">Open →</span></Link>)}</div> : <EmptyState icon="file" title="No CSV analyses yet" description="Upload a feature-only CSV to create a reviewable, paginated analysis." action={<Link className="button button-default" href="/csv">Open CSV analysis</Link>} />}
        {completed > 0 ? <div className="footer-note">{completed} completed job{completed === 1 ? "" : "s"} in this fetched page. Analysis predictions have no labels or precision/recall metrics.</div> : null}
      </Card>
    </div>

    <SectionHeading title="Recent transactions" description="Derived output only. Input feature values are not stored in API history." meta={history.data ? `${history.data.count} OF ${formatNumber(history.data.total ?? 0, 0)} ON THIS PAGE` : undefined} />
    <Card className="card-pad">
      {history.error ? <ErrorState error={history.error} onRetry={history.refresh} /> : history.loading ? <div className="loading-surface"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div> : records.length ? <div className="table-wrap"><table><thead><tr><th>Record</th><th>Timestamp</th><th>Risk tier</th><th>Fraud probability</th><th>Decision</th><th>Source</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{records.slice(0, 8).map((record) => <tr key={record.record_id}><td><span className="table-primary mono">{record.record_id.slice(0, 8)}…</span><span className="table-secondary">{record.model_version}</span></td><td>{formatDate(record.created_at)}</td><td><RiskBadge tier={record.risk_tier} /></td><td>{formatProbability(record.fraud_probability)}</td><td><span className={`badge ${record.predicted_class === 1 ? "tone-danger" : "tone-success"}`}>{record.predicted_class === 1 ? "Flagged for review" : "Not flagged by policy"}</span></td><td>{record.source ?? "API"}</td><td><Link className="table-action" href={`/transactions?record=${encodeURIComponent(record.record_id)}`}>Review</Link></td></tr>)}</tbody></table></div> : <EmptyState icon="transactions" title="History is empty" description="Predictions appear here after an analyst submits an explicit transaction or CSV analysis." action={<Link className="button button-primary" href="/predict">Make a prediction</Link>} />}
      {records.length ? <div className="pagination"><span>Showing the newest {Math.min(8, records.length)} of {formatNumber(history.data?.total ?? records.length, 0)} records</span><Link href="/transactions" className="table-action">Open transaction history →</Link></div> : null}
    </Card>
  </>;
}
