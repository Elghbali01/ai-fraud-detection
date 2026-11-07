"use client";

import Link from "next/link";
import { useMemo, useState, type FormEvent } from "react";
import { useApi } from "@/lib/use-api";
import { apiRequest } from "@/lib/api";
import { formatDate, formatNumber, formatProbability } from "@/lib/format";
import type { Investigation, PageResponse, Prediction } from "@/lib/types";
import { Button, Card, CardHeading, Field, PageHeader, RiskBadge } from "@/components/ui";

export function TransactionsPage({ initialRecordId }: { initialRecordId?: string }) {
  const [offset, setOffset] = useState(0);
  const [tier, setTier] = useState("");
  const [sort, setSort] = useState("desc");
  const [modelVersion, setModelVersion] = useState("");
  const [analysisId, setAnalysisId] = useState("");
  const [fromValue, setFromValue] = useState("");
  const [toValue, setToValue] = useState("");
  const [recordId, setRecordId] = useState(initialRecordId ?? "");
  const [showCaseForm, setShowCaseForm] = useState(false);
  const [title, setTitle] = useState("");
  const [reasonText, setReasonText] = useState("");
  const [actionError, setActionError] = useState("");
  const [actionBusy, setActionBusy] = useState(false);

  const query = useMemo(() => {
    const params = new URLSearchParams({ limit: "25", offset: String(offset), sort_order: sort });
    if (tier) params.set("risk_tier", tier);
    if (modelVersion.trim()) params.set("model_version", modelVersion.trim());
    if (analysisId.trim()) params.set("analysis_id", analysisId.trim());
    if (fromValue) params.set("from", new Date(fromValue).toISOString());
    if (toValue) params.set("to", new Date(toValue).toISOString());
    return `/history?${params.toString()}`;
  }, [offset, sort, tier, modelVersion, analysisId, fromValue, toValue]);
  const history = useApi<PageResponse<Prediction>>(query);
  const detail = useApi<Prediction>(recordId ? `/history/${encodeURIComponent(recordId)}` : null);
  const rows = history.data?.results ?? [];
  const lastPage = (history.data?.total ?? 0) === 0 || offset + 25 >= (history.data?.total ?? 0);

  async function createCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setActionError(""); setActionBusy(true);
    try {
      await apiRequest<Investigation>("/investigations", { method: "POST", body: JSON.stringify({ prediction_id: recordId, title, reason: reasonText }) });
      setShowCaseForm(false); setTitle(""); setReasonText("");
    } catch (reason) { setActionError(reason instanceof Error ? reason.message : "Investigation could not be created."); }
    finally { setActionBusy(false); }
  }

  return <>
    <PageHeader eyebrow="Workspace / transaction history" title="Transaction history" description="Browse persisted derived predictions with backend-supported filters and stable pagination. API history excludes input features." actions={<Link className="button button-primary" href="/predict">New prediction</Link>} />
    <Card className="card-pad">
      <CardHeading title="History filters" description="Date filters are converted to UTC before they are sent to the API." />
      <div className="form-row">
        <Field label="Risk tier"><select className="select" value={tier} onChange={(event) => { setOffset(0); setTier(event.target.value); }}><option value="">All tiers</option><option>Low</option><option>Elevated</option><option>High</option><option>Critical</option></select></Field>
        <Field label="Sort order"><select className="select" value={sort} onChange={(event) => { setOffset(0); setSort(event.target.value); }}><option value="desc">Newest first</option><option value="asc">Oldest first</option></select></Field>
        <Field label="Model version"><input className="input" value={modelVersion} onChange={(event) => { setOffset(0); setModelVersion(event.target.value); }} placeholder="Optional exact version" maxLength={160} /></Field>
        <Field label="Analysis ID"><input className="input" value={analysisId} onChange={(event) => { setOffset(0); setAnalysisId(event.target.value); }} placeholder="Optional UUID" maxLength={36} /></Field>
      </div>
      <details style={{ marginTop: 12 }}><summary className="field-label" style={{ cursor: "pointer" }}>Timestamp range</summary><div className="form-row" style={{ marginTop: 10 }}><Field label="From (UTC)"><input className="input" type="datetime-local" value={fromValue} onChange={(event) => { setOffset(0); setFromValue(event.target.value); }} /></Field><Field label="To (UTC)"><input className="input" type="datetime-local" value={toValue} onChange={(event) => { setOffset(0); setToValue(event.target.value); }} /></Field></div></details>
    </Card>

    <Card className="card-pad" style={{ marginTop: 14 }}><CardHeading title="Persisted predictions" description={history.data ? `${formatNumber(history.data.total, 0)} total rows match these filters.` : "Results are requested in pages of 25."} action={<button className="icon-button" aria-label="Refresh transaction history" onClick={history.refresh}><span aria-hidden="true">↻</span></button>} />
      {history.error ? <div className="error-state" role="alert"><div><h3>History request failed</h3><p>{history.error.message}</p><Button icon="refresh" onClick={history.refresh} style={{ marginTop: 8 }}>Retry</Button></div></div> : history.loading ? <div className="loading-surface"><div className="skeleton" /><div className="skeleton" /></div> : rows.length ? <div className="table-wrap"><table><thead><tr><th>Record ID</th><th>Created at</th><th>Source</th><th>Probability</th><th>Risk score</th><th>Tier</th><th>Decision</th><th>Review</th></tr></thead><tbody>{rows.map((row) => <tr key={row.record_id}><td className="mono">{row.record_id.slice(0, 10)}…</td><td>{formatDate(row.created_at)}</td><td>{row.source ?? "API"}{row.row_number ? <span className="table-secondary">CSV row {row.row_number}</span> : null}</td><td>{formatProbability(row.fraud_probability)}</td><td>{formatNumber(row.risk_score, 2)}</td><td><RiskBadge tier={row.risk_tier} /></td><td>{row.predicted_class === 1 ? "Flagged for review" : "Not flagged"}</td><td><button className="table-action" onClick={() => { setRecordId(row.record_id); setShowCaseForm(false); setActionError(""); }}>Open details</button></td></tr>)}</tbody></table></div> : <div className="empty-state"><span className="empty-icon">⌕</span><h3>No matching records</h3><p>Try removing filters or submit a transaction for review. No placeholder history is shown.</p><Link className="button button-default" href="/predict">Open prediction lab</Link></div>}
      <div className="pagination"><span>{history.data ? `Rows ${history.data.total ? offset + 1 : 0}–${Math.min(offset + rows.length, history.data.total ?? 0)} of ${formatNumber(history.data.total, 0)}` : "Waiting for API response"}</span><div className="pagination-controls"><button className="button button-default" disabled={offset === 0 || history.loading} onClick={() => setOffset((value) => Math.max(0, value - 25))}>Previous</button><button className="button button-default" disabled={lastPage || history.loading} onClick={() => setOffset((value) => value + 25)}>Next</button></div></div>
    </Card>

    {recordId ? <Card className="card-pad" style={{ marginTop: 14 }}><CardHeading title="Selected record" description={`Record ${recordId}`} action={<button className="button button-quiet" onClick={() => { setRecordId(""); setShowCaseForm(false); }}>Close</button>} />
      {detail.error ? <div className="error-state" role="alert"><div><h3>Record unavailable</h3><p>{detail.error.message}</p></div></div> : detail.loading ? <div className="skeleton skeleton-block" /> : detail.data ? <><div className="kv-grid"><div className="kv"><span className="kv-label">Model estimate</span><span className="kv-value">{formatProbability(detail.data.fraud_probability)}</span></div><div className="kv"><span className="kv-label">Risk category</span><span className="kv-value"><RiskBadge tier={detail.data.risk_tier} /></span></div><div className="kv"><span className="kv-label">Decision threshold</span><span className="kv-value">{formatProbability(detail.data.decision_threshold)}</span></div><div className="kv"><span className="kv-label">Anomaly score</span><span className="kv-value">{detail.data.anomaly ? `${formatNumber(detail.data.anomaly.score, 5)} · ${formatNumber(detail.data.anomaly.percentile, 1)}th percentile` : "Not returned"}</span></div><div className="kv"><span className="kv-label">Source</span><span className="kv-value">{detail.data.source ?? "API"}</span></div><div className="kv"><span className="kv-label">Policy version</span><span className="kv-value">{detail.data.risk_policy_version}</span></div></div><div className="form-actions" style={{ marginTop: 12 }}><Button icon="investigations" onClick={() => setShowCaseForm((value) => !value)}>Create investigation</Button><Link className="button button-default" href={`/anomalies?record=${encodeURIComponent(recordId)}`}>Separate anomaly review →</Link></div>{showCaseForm ? <form className="form-stack" style={{ marginTop: 14 }} onSubmit={createCase}><Field label="Case title"><input className="input" required maxLength={120} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Concise review title" /></Field><Field label="Reason"><textarea className="textarea" style={{ minHeight: 90 }} required maxLength={1000} value={reasonText} onChange={(event) => setReasonText(event.target.value)} placeholder="Analyst rationale; do not treat model output as ground truth." /></Field><div className="form-actions"><Button variant="primary" type="submit" disabled={actionBusy}>{actionBusy ? "Creating…" : "Create linked investigation"}</Button></div></form> : null}{actionError ? <p className="form-error" role="alert" style={{ marginTop: 10 }}>{actionError}</p> : null}<div className="footer-note">History stores derived scores only; transaction feature values are not recoverable here. Investigation outcomes are manually recorded analyst opinions, not ground truth.</div></> : null}
    </Card> : null}
  </>;
}
