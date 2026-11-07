"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { formatDate, formatNumber, formatProbability } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import type { Analysis, AnalysisResultsResponse, Prediction, RiskTier } from "@/lib/types";
import { Card, CardHeading, Callout, ErrorState, PageHeader, RiskBadge } from "@/components/ui";
import { TierDistribution } from "@/components/charts";

export function AnalysisDetailPage() {
  const params = useParams<{ analysisId: string }>();
  const router = useRouter();
  const analysisId = params.analysisId;
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const analysis = useApi<Analysis>(`/analyses/${encodeURIComponent(analysisId)}`);
  const summary = useApi<{ analysis_id: string; status: string; summary: Analysis["summary"] }>(`/analyses/${encodeURIComponent(analysisId)}/summary`);
  const results = useApi<AnalysisResultsResponse>(`/analyses/${encodeURIComponent(analysisId)}/results?limit=50&offset=${offset}`);
  const counts = summary.data?.summary?.risk_tier_counts as Partial<Record<RiskTier, number>> | undefined;
  const rows = results.data?.results ?? [];

  async function deleteAnalysis() {
    if (!window.confirm("Delete this analysis and its results? The upload file is removed when it is no longer referenced.")) return;
    setDeleting(true); setError("");
    try { await apiRequest(`/analyses/${encodeURIComponent(analysisId)}`, { method: "DELETE" }); router.push("/csv"); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Analysis could not be deleted."); setDeleting(false); }
  }

  return <>
    <PageHeader eyebrow="CSV analysis / detail" title="Analysis results" description="Paginated derived output for one server-validated upload. The analysis is not a labeled evaluation and does not establish fraud." actions={<Link className="button button-default" href="/csv">← All analyses</Link>} />
    {analysis.error ? <ErrorState error={analysis.error} onRetry={analysis.refresh} /> : analysis.loading ? <div className="skeleton skeleton-block" /> : analysis.data ? <>
      <Card className="card-pad"><CardHeading title="Analysis summary" description={`Created ${formatDate(analysis.data.created_at)} · model ${analysis.data.model_version ?? "unavailable"}`} action={<span className={`badge ${analysis.data.status === "completed" ? "tone-success" : analysis.data.status === "failed" ? "tone-danger" : "tone-warning"}`}>{analysis.data.status}</span>} />
        {analysis.data.status === "failed" ? <Callout tone="danger" icon="alert">Analysis failed with code <span className="mono">{analysis.data.failure_code ?? "unknown"}</span>. This API workflow does not resume interrupted jobs.</Callout> : null}
        <div className="grid grid-4" style={{ marginTop: 12 }}><div className="kv"><span className="kv-label">Rows requested</span><span className="kv-value">{formatNumber(analysis.data.requested_rows, 0)}</span></div><div className="kv"><span className="kv-label">Rows processed</span><span className="kv-value">{formatNumber(analysis.data.processed_rows, 0)}</span></div><div className="kv"><span className="kv-label">Flagged for review</span><span className="kv-value">{analysis.data.summary ? `${formatNumber(analysis.data.summary.flagged_for_review, 0)} · ${formatProbability((analysis.data.summary.flagged_percentage ?? 0) / 100)}` : "Pending"}</span></div><div className="kv"><span className="kv-label">Mean calibrated probability</span><span className="kv-value">{analysis.data.summary ? formatProbability(analysis.data.summary.mean_fraud_probability) : "Pending"}</span></div></div>
        <div className="form-actions" style={{ marginTop: 13 }}><button className="button button-danger" type="button" disabled={deleting || ["pending", "running"].includes(analysis.data.status)} onClick={deleteAnalysis}>{deleting ? "Deleting…" : "Delete analysis and results"}</button></div>
      </Card>

      {summary.error ? <div style={{ marginTop: 14 }}><ErrorState error={summary.error} onRetry={summary.refresh} /></div> : null}
      {analysis.data.summary ? <div className="grid grid-2" style={{ marginTop: 14 }}><Card className="card-pad"><CardHeading title="Risk tier distribution" description="Counts from the API summary." />{counts ? <TierDistribution counts={counts} /> : <p className="card-copy">No tier summary returned.</p>}</Card><Card className="card-pad"><CardHeading title="Anomaly category counts" description="Separate Isolation Forest signal." />{Object.keys(analysis.data.summary.anomaly_category_counts ?? {}).length ? <div className="kv-grid">{Object.entries(analysis.data.summary.anomaly_category_counts ?? {}).map(([category, value]) => <div className="kv" key={category}><span className="kv-label">{category}</span><span className="kv-value">{formatNumber(value, 0)}</span></div>)}</div> : <p className="card-copy">No anomaly categories are present in this summary.</p>}</Card></div> : null}
      <Card className="card-pad" style={{ marginTop: 14 }}><CardHeading title="Paginated results" description="API pages contain at most 50 rows here. Use next and previous to retrieve additional records." action={results.data ? <span className="badge">OFFSET {results.data.offset}</span> : undefined} />
        {results.error ? <ErrorState error={results.error} onRetry={results.refresh} /> : results.loading ? <div className="loading-surface"><div className="skeleton" /><div className="skeleton" /></div> : rows.length ? <div className="table-wrap"><table><thead><tr><th>Row</th><th>Record ID</th><th>Probability</th><th>Risk score</th><th>Tier</th><th>Decision</th><th>Anomaly</th></tr></thead><tbody>{rows.map((row: Prediction) => <tr key={row.record_id}><td>{formatNumber(row.row_number, 0)}</td><td className="mono">{row.record_id.slice(0, 10)}…</td><td>{formatProbability(row.fraud_probability)}</td><td>{formatNumber(row.risk_score, 2)}</td><td><RiskBadge tier={row.risk_tier} /></td><td>{row.predicted_class === 1 ? "Flagged" : "Not flagged"}</td><td>{row.anomaly?.category ?? "—"}</td></tr>)}</tbody></table></div> : <p className="card-copy">No rows have been returned for this offset.</p>}
        <div className="pagination"><span>Requested page: rows {offset + 1}–{Math.min(offset + 50, analysis.data.requested_rows)} of {formatNumber(analysis.data.requested_rows, 0)}</span><div className="pagination-controls"><button className="button button-default" disabled={offset === 0} onClick={() => setOffset((value) => Math.max(0, value - 50))}>Previous</button><button className="button button-default" disabled={offset + 50 >= analysis.data.requested_rows} onClick={() => setOffset((value) => value + 50)}>Next</button></div></div>
      </Card>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <div className="footer-note">Summary says labels_present={String(analysis.data.summary?.labels_present)} and precision_recall_computed={String(analysis.data.summary?.precision_recall_computed)}. Model scores are predictions for review; they are not confirmed outcomes.</div>
    </> : null}
  </>;
}
