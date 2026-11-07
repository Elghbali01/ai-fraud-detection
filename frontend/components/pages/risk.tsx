"use client";

import { useState, type FormEvent } from "react";
import { apiRequest } from "@/lib/api";
import { parseBatchJson, parseFeatureJson, featureTemplateText } from "@/lib/features";
import { formatNumber, formatProbability } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import type { Prediction, RiskTier } from "@/lib/types";
import { Button, Callout, Card, CardHeading, Field, PageHeader, RiskBadge } from "@/components/ui";

interface PriorityResult { input_index: number; fraud_probability: number; risk_score: number; risk_tier: RiskTier; predicted_class: number; [key: string]: unknown }
interface PriorityResponse { ranking_semantics: string; requested_count: number; selected_count: number; priority_policy: Record<string, unknown>; results: PriorityResult[] }

export function RiskPage() {
  const policy = useApi<Record<string, unknown>>("/risk/policy");
  const [singleText, setSingleText] = useState("");
  const [singleScore, setSingleScore] = useState<Prediction | null>(null);
  const [batchText, setBatchText] = useState("");
  const [budgetMode, setBudgetMode] = useState<"top_k" | "budget_percentage">("top_k");
  const [topK, setTopK] = useState("10");
  const [percentage, setPercentage] = useState("10");
  const [minScore, setMinScore] = useState("0");
  const [tiers, setTiers] = useState<RiskTier[]>(["Elevated", "High", "Critical"]);
  const [result, setResult] = useState<PriorityResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function scoreOne(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSingleScore(null);
    const parsed = parseFeatureJson(singleText);
    if (!parsed.ok) { setError(parsed.error); return; }
    setBusy(true);
    try { setSingleScore(await apiRequest<Prediction>("/risk/score", { method: "POST", body: JSON.stringify(parsed.value) })); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Risk scoring failed."); }
    finally { setBusy(false); }
  }

  function toggleTier(tier: RiskTier) {
    setTiers((current) => current.includes(tier) ? current.filter((item) => item !== tier) : [...current, tier]);
  }

  async function prioritize(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setResult(null);
    const parsed = parseBatchJson(batchText);
    if (!parsed.ok) { setError(parsed.error); return; }
    const amount = Number(budgetMode === "top_k" ? topK : percentage);
    const minimum = Number(minScore);
    if (!Number.isFinite(amount) || amount <= 0 || (budgetMode === "budget_percentage" && amount > 100)) { setError("Budget must be positive; a percentage must not exceed 100%."); return; }
    if (!Number.isFinite(minimum) || minimum < 0 || minimum > 100) { setError("Minimum risk score must be from 0 to 100."); return; }
    const body: Record<string, unknown> = { transactions: parsed.value, min_risk_score: minimum };
    body[budgetMode] = amount;
    if (tiers.length) body.risk_tiers = tiers;
    setBusy(true);
    try { setResult(await apiRequest<PriorityResponse>("/risk/prioritize", { method: "POST", body: JSON.stringify(body) })); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Prioritization failed."); }
    finally { setBusy(false); }
  }

  return <>
    <PageHeader eyebrow="Intelligence / risk policy" title="Risk intelligence" description="Review the persisted Mission 03 tier policy and prioritize an explicit bounded set of feature vectors. Ranking uses calibrated fraud probability and the backend’s stable tie behavior." />
    <div className="grid grid-main-side">
      <Card className="card-pad">
        <CardHeading title="Alert prioritization" description="The endpoint scores inputs in memory and returns a ranking; it does not persist these priority rows to history." />
        <form className="form-stack" onSubmit={prioritize}>
          <Field label="Transactions · JSON array" hint="1–1,000 exact-schema feature vectors. The sample button inserts a synthetic zero vector for contract testing only."><textarea className="textarea" aria-label="Transactions for prioritization" value={batchText} onChange={(event) => setBatchText(event.target.value)} placeholder={'[{ "Time": 1, "V1": 0, "…": "all fields", "Amount": 5 }]'} /></Field>
          <div className="tabs" role="tablist" aria-label="Alert budget mode"><button type="button" role="tab" aria-selected={budgetMode === "top_k"} className={`tab-button ${budgetMode === "top_k" ? "active" : ""}`} onClick={() => setBudgetMode("top_k")}>Top-K count</button><button type="button" role="tab" aria-selected={budgetMode === "budget_percentage"} className={`tab-button ${budgetMode === "budget_percentage" ? "active" : ""}`} onClick={() => setBudgetMode("budget_percentage")}>Percentage budget</button></div>
          <div className="form-row"><Field label={budgetMode === "top_k" ? "Maximum alerts" : "Review budget (%)"}><input className="input" type="number" min="0.01" max={budgetMode === "top_k" ? 1000 : 100} step="any" value={budgetMode === "top_k" ? topK : percentage} onChange={(event) => budgetMode === "top_k" ? setTopK(event.target.value) : setPercentage(event.target.value)} /></Field><Field label="Minimum risk score (0–100)"><input className="input" type="number" min="0" max="100" step="any" value={minScore} onChange={(event) => setMinScore(event.target.value)} /></Field></div>
          <fieldset style={{ padding: 0, border: 0 }}><legend className="field-label" style={{ marginBottom: 8 }}>Include operational tiers</legend><div className="toggle-row">{(["Low", "Elevated", "High", "Critical"] as RiskTier[]).map((tier) => <label className="choice" key={tier}><input type="checkbox" checked={tiers.includes(tier)} onChange={() => toggleTier(tier)} />{tier}</label>)}</div></fieldset>
          <div className="form-actions"><Button variant="primary" type="submit" disabled={busy}>{busy ? "Ranking…" : "Prioritize transactions"}</Button><Button type="button" icon="file" onClick={() => { setBatchText(`[${featureTemplateText()}]`); setError(""); }}>Insert synthetic vector</Button></div>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
        </form>
        <Callout tone="warning" icon="alert"><strong>Budget semantics.</strong> Supply exactly one Top-K count or percentage. Percentage budgets use the backend’s ceiling rule. Risk score is a 0–100 display mapping; anomaly signals are not blended into ranking.</Callout>
      </Card>
      <Card className="card-pad"><CardHeading title="Persisted risk policy" description="Thresholds and category semantics are served by GET /risk/policy." />{policy.error ? <div className="error-state" role="alert"><div><h3>Policy unavailable</h3><p>{policy.error.message}</p><Button icon="refresh" onClick={policy.refresh} style={{ marginTop: 8 }}>Retry</Button></div></div> : policy.loading ? <div className="loading-surface"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div> : policy.data ? <div className="stack-sm">{Object.entries(policy.data).filter(([key]) => key !== "semantics").map(([key, value]) => <div className="kv" key={key}><span className="kv-label">{key.replaceAll("_", " ")}</span><span className="kv-value">{typeof value === "object" ? JSON.stringify(value) : String(value)}</span></div>)}<div className="callout"><span aria-hidden="true">i</span><div>{String(policy.data.semantics ?? "Operational analyst triage categories.")}</div></div></div> : null}</Card>
    </div>

    <Card className="card-pad" style={{ marginTop: 14 }}><CardHeading title="Score one record" description="POST /risk/score persists one model result in transaction history." /><form className="form-stack" onSubmit={scoreOne}><Field label="Feature vector · JSON object"><textarea className="textarea" aria-label="Single risk score feature vector" value={singleText} onChange={(event) => setSingleText(event.target.value)} placeholder="Paste exactly Time, V1–V28 and Amount as finite numbers." /></Field><div className="form-actions"><Button variant="primary" type="submit" disabled={busy}>{busy ? "Scoring…" : "Score risk record"}</Button><Button type="button" icon="file" onClick={() => { setSingleText(featureTemplateText()); setError(""); }}>Insert explicit zero vector</Button></div></form>{singleScore ? <div className="result-hero" style={{ marginTop: 13 }}><div className="score-ring"><strong>{formatNumber(singleScore.risk_score, 1)}</strong><span>risk score</span></div><div><div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 5 }}><h3 className="result-title">{singleScore.predicted_class === 1 ? "Flagged for review" : "Not flagged by policy"}</h3><RiskBadge tier={singleScore.risk_tier} /></div><p className="result-copy">Model estimate {formatProbability(singleScore.fraud_probability)} · record {singleScore.record_id}</p></div></div> : null}{error ? <p className="form-error" role="alert" style={{ marginTop: 10 }}>{error}</p> : null}</Card>

    {result ? <Card className="card-pad" style={{ marginTop: 15 }}><CardHeading title="Prioritized review queue" description={`${result.selected_count} selected from ${result.requested_count} inputs · ${result.ranking_semantics}`} /><div className="kv-grid" style={{ marginBottom: 13 }}><div className="kv"><span className="kv-label">Selected</span><span className="kv-value">{formatNumber(result.selected_count, 0)}</span></div><div className="kv"><span className="kv-label">Scored</span><span className="kv-value">{formatNumber(result.requested_count, 0)}</span></div><div className="kv"><span className="kv-label">Budget rule</span><span className="kv-value">{budgetMode === "top_k" ? `Top ${topK}` : `${percentage}% · backend ceiling`}</span></div><div className="kv"><span className="kv-label">Minimum display score</span><span className="kv-value">{minScore}</span></div></div>{result.results.length ? <div className="table-wrap"><table><thead><tr><th>Rank</th><th>Input index</th><th>Probability</th><th>Risk score</th><th>Tier</th><th>Decision</th></tr></thead><tbody>{result.results.map((row, index) => <tr key={`${row.input_index}-${index}`}><td>{index + 1}</td><td>{row.input_index + 1}</td><td>{formatProbability(row.fraud_probability)}</td><td>{formatNumber(row.risk_score, 2)}</td><td><RiskBadge tier={row.risk_tier} /></td><td>{row.predicted_class === 1 ? "Flagged" : "Not flagged"}</td></tr>)}</tbody></table></div> : <p className="card-copy">The backend returned no rows in this priority budget.</p>}</Card> : null}
  </>;
}
