"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { apiRequest } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import type { Investigation, InvestigationOutcome, InvestigationStatus, PageResponse } from "@/lib/types";
import { Button, Card, CardHeading, EmptyState, ErrorState, Field, PageHeader, SectionHeading } from "@/components/ui";

const STATUSES: InvestigationStatus[] = ["Open", "In Review", "Escalated", "Closed"];
const OUTCOMES: InvestigationOutcome[] = ["Unconfirmed", "Legitimate", "Confirmed Fraud", "Inconclusive"];

const NEXT_STATUS: Record<InvestigationStatus, InvestigationStatus[]> = {
  Open: ["In Review", "Escalated", "Closed"],
  "In Review": ["Open", "Escalated", "Closed"],
  Escalated: ["In Review", "Closed"],
  Closed: [],
};

export function InvestigationsPage({ initialPredictionId }: { initialPredictionId?: string }) {
  const [statusFilter, setStatusFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const [predictionId, setPredictionId] = useState(initialPredictionId ?? "");
  const [title, setTitle] = useState("");
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [newStatus, setNewStatus] = useState<InvestigationStatus | "">("");
  const [newOutcome, setNewOutcome] = useState<InvestigationOutcome | "">("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const listPath = `/investigations?limit=50&offset=${offset}${statusFilter ? `&status=${encodeURIComponent(statusFilter)}` : ""}`;
  const list = useApi<PageResponse<Investigation>>(listPath);
  const detail = useApi<Investigation>(selectedId ? `/investigations/${encodeURIComponent(selectedId)}` : null);
  const rows = list.data?.investigations ?? [];

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    const body: Record<string, string> = { title: title.trim(), reason: reason.trim() };
    if (predictionId.trim()) body.prediction_id = predictionId.trim();
    try {
      const item = await apiRequest<Investigation>("/investigations", { method: "POST", body: JSON.stringify(body) });
      setSelectedId(item.investigation_id); setTitle(""); setReason(""); list.refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Investigation could not be created."); }
    finally { setBusy(false); }
  }

  async function update(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selectedId || (!newStatus && !newOutcome)) return;
    setError(""); setBusy(true);
    const body: Record<string, string> = {};
    if (newStatus) body.status = newStatus;
    if (newOutcome) body.outcome = newOutcome;
    try { await apiRequest<Investigation>(`/investigations/${encodeURIComponent(selectedId)}`, { method: "PATCH", body: JSON.stringify(body) }); setNewStatus(""); setNewOutcome(""); detail.refresh(); list.refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Investigation update failed."); }
    finally { setBusy(false); }
  }

  async function addNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selectedId || !note.trim()) return;
    setError(""); setBusy(true);
    try { await apiRequest(`/investigations/${encodeURIComponent(selectedId)}/notes`, { method: "POST", body: JSON.stringify({ body: note.trim() }) }); setNote(""); detail.refresh(); list.refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Note could not be added."); }
    finally { setBusy(false); }
  }

  return <>
    <PageHeader eyebrow="Operations / analyst workflow" title="Investigation workspace" description="Create review cases, record allowed status transitions, and append analyst notes. Outcomes are manually recorded opinions and are explicitly not ground truth." />
    <div className="grid grid-main-side">
      <Card className="card-pad"><CardHeading title="Create an investigation" description="A prediction link is optional. No analyst identity or login is fabricated." /><form className="form-stack" onSubmit={create}><Field label="Case title"><input className="input" required minLength={1} maxLength={120} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Concise reason for review" /></Field><Field label="Reason"><textarea className="textarea" style={{ minHeight: 95 }} required minLength={1} maxLength={1000} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Record why this case needs analyst review." /></Field><Field label="Prediction record ID · optional"><input className="input mono" maxLength={36} value={predictionId} onChange={(event) => setPredictionId(event.target.value)} placeholder="UUID from transaction history" /></Field><Button variant="primary" type="submit" icon="plus" disabled={busy}>{busy ? "Creating…" : "Create investigation"}</Button></form>{error ? <p className="form-error" role="alert" style={{ marginTop: 10 }}>{error}</p> : null}</Card>
      <Card className="card-pad"><CardHeading title="Workflow guardrails" description="Status transitions follow the backend state machine." /><div className="stack-sm">{STATUSES.map((status) => <div className="analysis-card" key={status}><span className={`badge ${status === "Escalated" ? "tone-danger" : status === "Closed" ? "tone-neutral" : status === "In Review" ? "tone-warning" : "tone-success"}`}>{status}</span><span className="card-copy">{status === "Closed" ? "Closed cases cannot be reopened through this API." : `Allowed next state${NEXT_STATUS[status].length === 1 ? "" : "s"}: ${NEXT_STATUS[status].join(", ") || "none"}`}</span></div>)}</div><div className="callout" style={{ marginTop: 12 }}><span aria-hidden="true">i</span><div>Investigation history is stored in the local SQLite database. Notes are local user text; the database is not encrypted at rest.</div></div></Card>
    </div>

    <SectionHeading title="Persisted cases" description="Only records returned by the local API are shown." meta={list.data ? `${formatNumber(list.data.count, 0)} ON THIS PAGE` : undefined} />
    <Card className="card-pad"><div className="form-row" style={{ marginBottom: 13 }}><Field label="Filter by status"><select className="select" value={statusFilter} onChange={(event) => { setOffset(0); setStatusFilter(event.target.value); }}><option value="">All statuses</option>{STATUSES.map((item) => <option key={item}>{item}</option>)}</select></Field></div>
      {list.error ? <ErrorState error={list.error} onRetry={list.refresh} /> : list.loading ? <div className="loading-surface"><div className="skeleton" /><div className="skeleton" /></div> : rows.length ? <div className="table-wrap"><table><thead><tr><th>Title</th><th>Status</th><th>Outcome</th><th>Linked record</th><th>Updated</th><th>Details</th></tr></thead><tbody>{rows.map((item) => <tr key={item.investigation_id}><td><span className="table-primary">{item.title}</span><span className="table-secondary">{item.investigation_id}</span></td><td><span className={`badge ${item.status === "Escalated" ? "tone-danger" : item.status === "In Review" ? "tone-warning" : item.status === "Closed" ? "tone-neutral" : "tone-success"}`}>{item.status}</span></td><td>{item.outcome ?? "Not recorded"}</td><td className="mono">{item.prediction_id ? `${item.prediction_id.slice(0, 8)}…` : "—"}</td><td>{formatDate(item.updated_at)}</td><td><button className="table-action" onClick={() => { setSelectedId(item.investigation_id); setError(""); }}>Open case</button></td></tr>)}</tbody></table></div> : <EmptyState icon="investigations" title="No investigations found" description="Create a case from this page or link it to a prediction from transaction history." />}
      <div className="pagination"><span>API page size: 50</span><div className="pagination-controls"><button className="button button-default" disabled={!offset || list.loading} onClick={() => setOffset((value) => Math.max(0, value - 50))}>Previous</button><button className="button button-default" disabled={rows.length < 50 || list.loading} onClick={() => setOffset((value) => value + 50)}>Next</button></div></div>
    </Card>

    {selectedId ? <Card className="card-pad" style={{ marginTop: 14 }}><CardHeading title="Investigation details" description={selectedId} action={<button className="button button-quiet" onClick={() => setSelectedId("")}>Close</button>} />
      {detail.error ? <ErrorState error={detail.error} onRetry={detail.refresh} /> : detail.loading ? <div className="skeleton skeleton-block" /> : detail.data ? <div className="stack">
        <div className="kv-grid"><div className="kv"><span className="kv-label">Title</span><span className="kv-value">{detail.data.title}</span></div><div className="kv"><span className="kv-label">Current status</span><span className="kv-value">{detail.data.status}</span></div><div className="kv"><span className="kv-label">Analyst-recorded outcome</span><span className="kv-value">{detail.data.outcome ?? "Not recorded"}</span></div><div className="kv"><span className="kv-label">Ground truth</span><span className="kv-value">No · API marks false</span></div></div>
        <p className="card-copy">{detail.data.reason}</p>
        {detail.data.prediction_id ? <p className="card-copy">Linked prediction: <Link className="table-action" href={`/transactions?record=${encodeURIComponent(detail.data.prediction_id)}`}>{detail.data.prediction_id}</Link></p> : null}
        <form className="form-row" onSubmit={update}><Field label="Next status"><select className="select" value={newStatus} onChange={(event) => setNewStatus(event.target.value as InvestigationStatus | "")}><option value="">Keep current</option>{NEXT_STATUS[detail.data.status].map((status) => <option value={status} key={status}>{status}</option>)}</select></Field><Field label="Record analyst outcome"><select className="select" value={newOutcome} onChange={(event) => setNewOutcome(event.target.value as InvestigationOutcome | "")}><option value="">Keep current</option>{OUTCOMES.map((outcome) => <option value={outcome} key={outcome}>{outcome}</option>)}</select></Field><Button type="submit" variant="primary" disabled={busy || (!newStatus && !newOutcome)}>Save changes</Button></form>
        <form className="form-row" onSubmit={addNote}><Field label="Append a note"><input className="input" required minLength={1} maxLength={4000} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add analyst context" /></Field><Button type="submit" disabled={busy || !note.trim()}>Add note</Button></form>
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        <div className="grid grid-2"><div><h3 className="card-title">Notes</h3>{detail.data.notes?.length ? <div className="stack-sm" style={{ marginTop: 9 }}>{detail.data.notes.map((item) => <div className="kv" key={item.note_id}><span className="card-copy">{item.body}</span><span className="table-secondary">{formatDate(item.created_at)}</span></div>)}</div> : <p className="card-copy" style={{ marginTop: 7 }}>No notes recorded.</p>}</div><div><h3 className="card-title">Workflow events</h3>{detail.data.events?.length ? <div className="stack-sm" style={{ marginTop: 9 }}>{detail.data.events.map((event) => <div className="kv" key={event.event_id}><span className="kv-value">{event.event_type.replaceAll("_", " ")}</span><span className="table-secondary">{event.old_value ?? "—"} → {event.new_value ?? "—"} · {formatDate(event.created_at)}</span></div>)}</div> : <p className="card-copy" style={{ marginTop: 7 }}>No workflow events returned.</p>}</div></div>
        <div className="callout callout-warning"><span aria-hidden="true">!</span><div>Outcome recorded: <strong>{String(detail.data.outcome_is_analyst_recorded)}</strong> · ground truth: <strong>{String(detail.data.outcome_is_ground_truth)}</strong>. Treat this as an analyst workflow note, not an adjudicated label.</div></div>
      </div> : null}
    </Card> : null}
  </>;
}
