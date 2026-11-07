"use client";

import { useState, type FormEvent } from "react";
import { apiRequest } from "@/lib/api";
import { parseBatchJson, featureTemplateText } from "@/lib/features";
import { formatNumber } from "@/lib/format";
import { Button, Callout, Card, CardHeading, Field, PageHeader } from "@/components/ui";

interface AnomalyResponse { model_version: string; score_direction: string; score_is_probability: false; fraud_probability_included: false; results: Array<{ anomaly_score: number; percentile: number; category: string }> }

export function AnomalyPage({ initialRecordId }: { initialRecordId?: string }) {
  const [batchText, setBatchText] = useState("");
  const [result, setResult] = useState<AnomalyResponse | null>(null);
  const [error, setError] = useState(initialRecordId ? "History stores derived scores only; the original feature values are not retained. Paste the feature vector to request a separate anomaly score." : "");
  const [busy, setBusy] = useState(false);

  async function score(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setResult(null);
    const parsed = parseBatchJson(batchText);
    if (!parsed.ok) { setError(parsed.error); return; }
    setBusy(true);
    try { setResult(await apiRequest<AnomalyResponse>("/anomalies/score", { method: "POST", body: JSON.stringify({ transactions: parsed.value }) })); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Anomaly scoring failed."); }
    finally { setBusy(false); }
  }

  const rows = result?.results ?? [];
  return <>
    <PageHeader eyebrow="Intelligence / unsupervised signal" title="Anomaly intelligence" description="Score explicit feature vectors with the separate Isolation Forest service. This page does not blend anomaly output with supervised fraud probability or the risk-tier policy." />
    <Callout tone="warning" icon="alert"><strong>Separate signal.</strong> A higher anomaly score means more anomalous relative to the training reference. It is not a probability of fraud and is not included in prioritization.</Callout>
    <div className="grid grid-main-side" style={{ marginTop: 14 }}>
      <Card className="card-pad"><CardHeading title="Score feature vectors" description="One or more exact-schema numeric vectors; bounded by the API batch limit." /><form className="form-stack" onSubmit={score}><Field label="Transactions · JSON array"><textarea className="textarea" aria-label="Transactions for anomaly scoring" value={batchText} onChange={(event) => setBatchText(event.target.value)} placeholder="Paste an array of feature vectors." /></Field><div className="form-actions"><Button variant="primary" type="submit" icon="anomaly" disabled={busy}>{busy ? "Scoring…" : "Score anomaly signal"}</Button><Button type="button" icon="file" onClick={() => setBatchText(`[${featureTemplateText()}]`)}>Insert explicit zero vector</Button></div>{error ? <p className="form-error" role="alert">{error}</p> : null}</form></Card>
      <Card className="card-pad"><CardHeading title="Signal interpretation" description="Returned directly by POST /anomalies/score." /><div className="stack-sm"><div className="kv"><span className="kv-label">Score direction</span><span className="kv-value">Higher = more anomalous</span></div><div className="kv"><span className="kv-label">Probability semantics</span><span className="kv-value">Not a probability</span></div><div className="kv"><span className="kv-label">Fraud probability included</span><span className="kv-value">No</span></div><div className="kv"><span className="kv-label">Training reference</span><span className="kv-value">Percentile categories returned by API</span></div></div></Card>
    </div>
    {result ? <Card className="card-pad" style={{ marginTop: 14 }}><CardHeading title="Anomaly results" description={`Model ${result.model_version} · ${rows.length} row${rows.length === 1 ? "" : "s"}`} /><div className="table-wrap"><table><thead><tr><th>Input index</th><th>Anomaly score</th><th>Training-reference percentile</th><th>Category</th></tr></thead><tbody>{rows.map((row, index) => <tr key={index}><td>{index + 1}</td><td>{formatNumber(row.anomaly_score, 6)}</td><td>{formatNumber(row.percentile, 2)}th</td><td><span className={`badge ${row.category.toLowerCase().includes("high") ? "tone-danger" : row.category.toLowerCase().includes("moderate") ? "tone-warning" : "tone-neutral"}`}>{row.category}</span></td></tr>)}</tbody></table></div><div className="footer-note">No fraud-probability field is present in the anomaly response. Score is for analyst triage only.</div></Card> : null}
  </>;
}
