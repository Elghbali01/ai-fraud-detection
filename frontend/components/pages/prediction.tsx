"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ShapWaterfall } from "@/components/charts";
import { Button, Callout, Card, CardHeading, Field, PageHeader, RiskBadge } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { filterAndSortBatch, type BatchSort } from "@/lib/batch";
import { featureTemplateText, parseBatchJson, parseFeatureInputs } from "@/lib/features";
import { formatNumber, formatProbability } from "@/lib/format";
import { FEATURE_COLUMNS, type FeatureName, type LocalExplanation, type Prediction, type PredictionResponse, type RiskTier } from "@/lib/types";

type Mode = "single" | "batch";

const PCA_GROUPS = [
  { title: "Components V1–V7", fields: FEATURE_COLUMNS.slice(1, 8) },
  { title: "Components V8–V14", fields: FEATURE_COLUMNS.slice(8, 15) },
  { title: "Components V15–V21", fields: FEATURE_COLUMNS.slice(15, 22) },
  { title: "Components V22–V28", fields: FEATURE_COLUMNS.slice(22, 29) },
];

export function PredictionPage() {
  const [mode, setMode] = useState<Mode>("single");
  const [singleValues, setSingleValues] = useState<Partial<Record<FeatureName, string>>>({});
  const [featureSearch, setFeatureSearch] = useState("");
  const [batchText, setBatchText] = useState("");
  const [batchTier, setBatchTier] = useState<"" | RiskTier>("");
  const [batchSort, setBatchSort] = useState<BatchSort>("input");
  const [result, setResult] = useState<Prediction | null>(null);
  const [batchResult, setBatchResult] = useState<PredictionResponse | null>(null);
  const [explanation, setExplanation] = useState<LocalExplanation | null>(null);
  const [method, setMethod] = useState("linear_log_odds");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function updateFeature(name: FeatureName, value: string) {
    setSingleValues((current) => ({ ...current, [name]: value }));
    setResult(null);
    setExplanation(null);
    setError("");
  }

  function clearSingle() {
    setSingleValues({});
    setResult(null);
    setExplanation(null);
    setError("");
  }

  function currentVector() {
    return parseFeatureInputs(singleValues);
  }

  async function submitSingle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    setExplanation(null);
    setBatchResult(null);
    const parsed = currentVector();
    if (!parsed.ok) {
      setError(parsed.error);
      return;
    }
    setBusy(true);
    try {
      setResult(await apiRequest<Prediction>("/predictions", {
        method: "POST",
        body: JSON.stringify(parsed.value),
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Prediction failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitBatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    setExplanation(null);
    setBatchResult(null);
    const parsed = parseBatchJson(batchText);
    if (!parsed.ok) {
      setError(parsed.error);
      return;
    }
    setBusy(true);
    try {
      setBatchResult(await apiRequest<PredictionResponse>("/predictions/batch", {
        method: "POST",
        body: JSON.stringify({ transactions: parsed.value, include_explanations: false }),
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Batch prediction failed.");
    } finally {
      setBusy(false);
    }
  }

  async function explainCurrent() {
    const parsed = currentVector();
    if (!parsed.ok) {
      setError(parsed.error);
      return;
    }
    setError("");
    setBusy(true);
    try {
      setExplanation(await apiRequest<LocalExplanation>("/explanations/local", {
        method: "POST",
        body: JSON.stringify({ features: parsed.value, method, top_n: 30 }),
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Explanation request failed.");
    } finally {
      setBusy(false);
    }
  }

  const search = featureSearch.trim().toLowerCase();
  const visiblePcaGroups = PCA_GROUPS.map((group) => ({
    ...group,
    fields: group.fields.filter((field) => !search || field.toLowerCase().includes(search)),
  })).filter((group) => group.fields.length > 0);
  const localContributions = explanation?.explanation?.feature_contributions ?? explanation?.contributions ?? [];
  const localBaseValue = Number(explanation?.explanation?.base_value ?? 0);
  const localOutputValue = Number(explanation?.raw_decision_score ?? 0);
  const displayedBatchResults = filterAndSortBatch(batchResult?.results ?? [], batchTier, batchSort);

  return <>
    <PageHeader
      eyebrow="Workspace / prediction"
      title="Prediction lab"
      description="Score one transaction or a bounded batch with the frozen backend model. Each prediction is persisted to local history; provide real feature values before submitting."
    />
    <div className="tabs" role="tablist" aria-label="Prediction mode">
      <button type="button" role="tab" aria-selected={mode === "single"} className={`tab-button ${mode === "single" ? "active" : ""}`} onClick={() => { setMode("single"); setError(""); }}>Single transaction</button>
      <button type="button" role="tab" aria-selected={mode === "batch"} className={`tab-button ${mode === "batch" ? "active" : ""}`} onClick={() => { setMode("batch"); setError(""); }}>Batch scoring</button>
    </div>

    <div className="grid grid-main-side" style={{ marginTop: 14 }}>
      <Card className="card-pad">
        {mode === "single" ? <>
          <CardHeading title="Transaction feature inputs" description="All 30 numeric fields are required. Time is elapsed seconds; Amount is in dataset units, with no currency assumed." />
          <form className="form-stack" onSubmit={submitSingle}>
            <fieldset className="feature-fieldset">
              <legend className="feature-legend">Transaction context</legend>
              <div className="feature-grid feature-grid-context">
                <Field label="Time" hint="Elapsed seconds from the dataset origin; not a calendar timestamp.">
                  <input className="input" type="number" step="any" inputMode="decimal" aria-label="Time" aria-required="true" value={singleValues.Time ?? ""} onChange={(event) => updateFeature("Time", event.target.value)} placeholder="Required" />
                </Field>
                <Field label="Amount" hint="Dataset units. No currency is inferred.">
                  <input className="input" type="number" step="any" inputMode="decimal" aria-label="Amount" aria-required="true" value={singleValues.Amount ?? ""} onChange={(event) => updateFeature("Amount", event.target.value)} placeholder="Required" />
                </Field>
              </div>
            </fieldset>

            <details className="feature-disclosure">
              <summary>Anonymized PCA components <span>V1–V28 · required</span></summary>
              <p className="field-hint">V1–V28 are anonymized PCA-derived coordinates. They have no asserted merchant, customer, location, device, or other business meaning.</p>
              <Field label="Find a PCA feature"><input className="input" type="search" aria-label="Search PCA features" placeholder="Search V1–V28" value={featureSearch} onChange={(event) => setFeatureSearch(event.target.value)} /></Field>
              <div className="pca-groups">
                {visiblePcaGroups.map((group) => <fieldset className="feature-fieldset pca-group" key={group.title}>
                  <legend className="feature-legend">{group.title}</legend>
                  <div className="feature-grid">
                    {group.fields.map((field) => <Field key={field} label={field}>
                      <input className="input" type="number" step="any" inputMode="decimal" aria-label={field} aria-required="true" value={singleValues[field as FeatureName] ?? ""} onChange={(event) => updateFeature(field as FeatureName, event.target.value)} placeholder="Required" />
                    </Field>)}
                  </div>
                </fieldset>)}
                {visiblePcaGroups.length === 0 ? <p className="field-hint">No PCA component matches “{featureSearch}”.</p> : null}
              </div>
            </details>

            <div className="form-actions">
              <Button variant="primary" type="submit" disabled={busy}>{busy ? "Scoring…" : "Score transaction"}</Button>
              <Button type="button" icon="file" disabled={busy} onClick={() => { setSingleValues(Object.fromEntries(FEATURE_COLUMNS.map((name) => [name, "0"])) as Partial<Record<FeatureName, string>>); setResult(null); setExplanation(null); setError(""); }}>Insert zero-filled template</Button>
              <Button type="button" variant="quiet" disabled={busy} onClick={clearSingle}>Reset values</Button>
            </div>
          </form>
          <Callout tone="warning" icon="alert"><strong>Template warning.</strong> The zero-filled helper is a placeholder vector, not an observed transaction. Replace every value before scoring. Submissions are stored in API history.</Callout>
        </> : <>
          <CardHeading title="Bounded batch" description="Submit 1–1,000 transactions. Explanations are disabled for the batch to keep scoring bounded; request a local explanation separately." />
          <form className="form-stack" onSubmit={submitBatch}>
            <Field label="Feature vectors · JSON array" hint="Paste an array of exact-schema objects. An object with a transactions array is also accepted."><textarea className="textarea" aria-label="Batch feature vectors JSON" value={batchText} onChange={(event) => setBatchText(event.target.value)} placeholder={'[\n  { "Time": 0, "V1": 0, "…": "all V fields", "Amount": 0 }\n]'} /></Field>
            <div className="form-actions"><Button variant="primary" type="submit" disabled={busy}>{busy ? "Scoring batch…" : "Score batch"}</Button><Button type="button" icon="file" onClick={() => { setBatchText(JSON.stringify([JSON.parse(featureTemplateText())], null, 2)); setError(""); }}>Insert one zero-filled row</Button></div>
          </form>
          <Callout tone="warning" icon="alert"><strong>Batch persistence.</strong> Every submitted output is added to history. The sample helper is explicitly synthetic and should be replaced before sending a real review.</Callout>
        </>}
        {error ? <p className="form-error" role="alert" style={{ marginTop: 12 }}>{error}</p> : null}
      </Card>

      <div className="stack">
        <Card className="card-pad"><CardHeading title="Decision semantics" description="Four distinct values are returned by the backend." /><div className="stack-sm"><div className="kv"><span className="kv-label">Fraud probability</span><span className="kv-value">Sigmoid-calibrated model estimate</span></div><div className="kv"><span className="kv-label">Risk score</span><span className="kv-value">0–100 display mapping</span></div><div className="kv"><span className="kv-label">Predicted class</span><span className="kv-value">Frozen threshold decision</span></div><div className="kv"><span className="kv-label">Risk tier</span><span className="kv-value">Persisted operational triage policy</span></div></div></Card>
        <Callout icon="shield">A model flag is a review signal. It is not proof of fraud, account behavior, or a confirmed analyst outcome.</Callout>
      </div>
    </div>

    {result ? <Card className="card-pad" style={{ marginTop: 15 }}><CardHeading title="Prediction result" description={`Persisted record ${result.record_id}`} action={<Link className="button button-default" href={`/investigations?predictionId=${encodeURIComponent(result.record_id)}`}>Open investigation →</Link>} /><div className="result-hero"><div className="score-ring"><strong>{formatNumber(result.risk_score, 1)}</strong><span>risk score</span></div><div><div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 9, marginBottom: 6 }}><h3 className="result-title">{result.predicted_class === 1 ? "Flagged for review" : "Not flagged by policy"}</h3><RiskBadge tier={result.risk_tier} /></div><p className="result-copy">Calibrated model estimate: {formatProbability(result.fraud_probability)} · frozen threshold: {formatProbability(result.decision_threshold)} · decision: {result.decision_status.replaceAll("_", " ")}</p></div></div><div className="kv-grid" style={{ marginTop: 12 }}><div className="kv"><span className="kv-label">Model version</span><span className="kv-value">{result.model_version}</span></div><div className="kv"><span className="kv-label">Calibration status</span><span className="kv-value">{result.probability_calibration_status}</span></div><div className="kv"><span className="kv-label">Policy version</span><span className="kv-value">{result.risk_policy_version}</span></div><div className="kv"><span className="kv-label">Anomaly signal · separate model</span><span className="kv-value">{result.anomaly ? `${result.anomaly.category ?? "Scored"} · ${formatNumber(result.anomaly.percentile, 1)}th percentile` : "Unavailable in prediction response"}</span></div></div><div className="form-row" style={{ marginTop: 13 }}><Field label="Local explanation method"><select className="select" aria-label="Explanation method" value={method} onChange={(event) => setMethod(event.target.value)}><option value="linear_log_odds">Exact linear · raw log-odds</option><option value="shap_interventional_log_odds">Interventional SHAP · raw log-odds</option></select></Field><Button icon="explain" disabled={busy} onClick={explainCurrent}>{busy ? "Explaining…" : "Explain this vector"}</Button></div><div className="footer-note">The explanation endpoint accepts the feature vector again because API history stores derived scores only and does not retain input features.</div></Card> : null}

    {explanation ? <Card className="card-pad" style={{ marginTop: 15 }}><CardHeading title="Local explanation · raw log-odds" description={`${String(explanation.explanation?.method ?? method)} · feature contributions are not additive to the later calibrated probability.`} /><div className="kv-grid" style={{ marginBottom: 12 }}><div className="kv"><span className="kv-label">Baseline log-odds</span><span className="kv-value">{formatNumber(localBaseValue, 5)}</span></div><div className="kv"><span className="kv-label">Raw model output</span><span className="kv-value">{formatNumber(localOutputValue, 5)}</span></div><div className="kv"><span className="kv-label">Reconstruction residual</span><span className="kv-value">{formatNumber(explanation.explanation?.reconstruction_error, 9)}</span></div></div><p className="card-copy">{explanation.explanation?.baseline_semantics ?? "The baseline and feature contributions describe raw model log-odds."} {explanation.explanation?.all_contributions_returned ? "All 30 feature contributions are shown." : "The returned contributions may not reconstruct the full output."}</p><ShapWaterfall baseValue={localBaseValue} outputValue={localOutputValue} contributions={localContributions} /></Card> : null}

    {batchResult ? <Card className="card-pad" style={{ marginTop: 15 }}><CardHeading title="Batch results" description={`${batchResult.count} persisted predictions. Input vectors are not retained in history.`} /><div className="form-row batch-controls"><Field label="Filter risk tier"><select className="select" aria-label="Filter batch by risk tier" value={batchTier} onChange={(event) => setBatchTier(event.target.value as "" | RiskTier)}><option value="">All tiers</option><option>Low</option><option>Elevated</option><option>High</option><option>Critical</option></select></Field><Field label="Sort results"><select className="select" aria-label="Sort batch results" value={batchSort} onChange={(event) => setBatchSort(event.target.value as typeof batchSort)}><option value="input">Input order</option><option value="probability_desc">Probability · high to low</option><option value="probability_asc">Probability · low to high</option><option value="risk_desc">Risk score · high to low</option></select></Field></div>{displayedBatchResults.length ? <div className="table-wrap"><table><thead><tr><th>Rank</th><th>Record ID</th><th>Fraud probability</th><th>Risk score</th><th>Tier</th><th>Decision</th></tr></thead><tbody>{displayedBatchResults.map((row, index) => <tr key={row.record_id}><td>{index + 1}</td><td className="mono">{row.record_id.slice(0, 10)}…</td><td>{formatProbability(row.fraud_probability)}</td><td>{formatNumber(row.risk_score, 2)}</td><td><RiskBadge tier={row.risk_tier} /></td><td>{row.predicted_class === 1 ? "Flagged for review" : "Not flagged by policy"}</td></tr>)}</tbody></table></div> : <p className="card-copy">No batch rows match this risk tier filter.</p>}<div className="pagination"><span>Showing {displayedBatchResults.length} of {batchResult.count} · real API results</span><Link className="table-action" href="/transactions">Review persisted history →</Link></div></Card> : null}
  </>;
}
