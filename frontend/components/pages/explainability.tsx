"use client";

import { useState, type FormEvent } from "react";
import { apiRequest } from "@/lib/api";
import { featureTemplateText, parseFeatureJson } from "@/lib/features";
import { formatNumber, formatProbability } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import type { LocalExplanation } from "@/lib/types";
import { Button, Callout, Card, CardHeading, Field, PageHeader } from "@/components/ui";
import { HorizontalBars, ShapWaterfall } from "@/components/charts";

interface GlobalSummary { model_version: string; output_space: string; summary_method: string; partition: string; features: Array<Record<string, unknown>>; calibrated_probability_additivity_claim: false; causal_claim: false }

export function ExplainabilityPage() {
  const global = useApi<GlobalSummary>("/explanations/global");
  const [featureText, setFeatureText] = useState("");
  const [method, setMethod] = useState("linear_log_odds");
  const [explanation, setExplanation] = useState<LocalExplanation | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function explain(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setExplanation(null);
    const parsed = parseFeatureJson(featureText);
    if (!parsed.ok) { setError(parsed.error); return; }
    setBusy(true);
    try { setExplanation(await apiRequest<LocalExplanation>("/explanations/local", { method: "POST", body: JSON.stringify({ features: parsed.value, method, top_n: 30 }) })); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Explanation request failed."); }
    finally { setBusy(false); }
  }

  const details = explanation?.explanation as { base_value?: number; feature_contributions?: Array<Record<string, unknown>>; all_contributions_returned?: boolean; top_positive_features?: unknown[]; top_negative_features?: unknown[]; baseline_semantics?: string; reconstruction_error?: number } | undefined;
  return <>
    <PageHeader eyebrow="Intelligence / explainable AI" title="Explainability explorer" description="Inspect global validation-time SHAP summaries and request a bounded local explanation for a supplied feature vector. Attribution values are served by the real Mission 04 API." />
    <Callout tone="warning" icon="alert"><strong>Output-space boundary.</strong> Linear and SHAP contributions are in raw model log-odds. They are not direct additions to the later calibrated fraud probability, and they do not imply causality. V1–V28 are anonymized PCA features.</Callout>

    <div className="grid grid-2" style={{ marginTop: 14 }}>
      <Card className="card-pad"><CardHeading title="Global SHAP baseline" description="Precomputed from the frozen model’s validation partition; this is not a live transaction feed." action={global.data ? <span className="badge">{global.data.partition.toUpperCase()} PARTITION</span> : undefined} />
        {global.error ? <div className="error-state" role="alert"><div><h3>Global summary unavailable</h3><p>{global.error.message}</p><Button icon="refresh" onClick={global.refresh} style={{ marginTop: 8 }}>Retry</Button></div></div> : global.loading ? <div className="loading-surface"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div> : global.data ? <><div className="kv-grid" style={{ marginBottom: 13 }}><div className="kv"><span className="kv-label">Model</span><span className="kv-value">{global.data.model_version}</span></div><div className="kv"><span className="kv-label">Output space</span><span className="kv-value">{global.data.output_space}</span></div></div><HorizontalBars values={global.data.features.slice(0, 12)} labelKey="feature" valueKey="mean_abs_shap_log_odds" /><div className="footer-note">Bars show mean absolute validation SHAP magnitude. The signed mean is returned by the API separately. Causal claim: {String(global.data.causal_claim)}.</div></> : null}
      </Card>

      <Card className="card-pad"><CardHeading title="Local explanation" description="Submit the exact 30-feature vector to the local explanation endpoint." />
        <form className="form-stack" onSubmit={explain}><Field label="Feature vector · JSON object"><textarea className="textarea" aria-label="Explanation feature vector JSON" value={featureText} onChange={(event) => setFeatureText(event.target.value)} placeholder="Paste Time, V1–V28 and Amount as finite numbers." /></Field><Field label="Attribution method"><select className="select" value={method} onChange={(event) => setMethod(event.target.value)}><option value="linear_log_odds">Exact linear · raw log-odds</option><option value="shap_interventional_log_odds">Interventional SHAP · raw log-odds</option></select></Field><div className="form-actions"><Button variant="primary" type="submit" icon="explain" disabled={busy}>{busy ? "Explaining…" : "Explain supplied vector"}</Button><Button type="button" icon="file" onClick={() => { setFeatureText(featureTemplateText()); setError(""); }}>Insert zero-filled vector</Button></div>{error ? <p className="form-error" role="alert">{error}</p> : null}</form>
      </Card>
    </div>

    {explanation ? <Card className="card-pad" style={{ marginTop: 14 }}><CardHeading title="Local attribution" description={`${String(explanation.method ?? method)} · ${String(explanation.model_version ?? "")}`} action={<span className="badge">RAW LOG-ODDS</span>} /><div className="kv-grid" style={{ marginBottom: 11 }}><div className="kv"><span className="kv-label">Calibrated model estimate</span><span className="kv-value">{formatProbability(Number(explanation.fraud_probability))}</span></div><div className="kv"><span className="kv-label">Raw estimator output</span><span className="kv-value">{formatNumber(Number(explanation.raw_decision_score), 5)}</span></div><div className="kv"><span className="kv-label">Attribution residual</span><span className="kv-value">{formatNumber(details?.reconstruction_error, 9)}</span></div><div className="kv"><span className="kv-label">Decision threshold</span><span className="kv-value">{formatProbability(Number(explanation.decision_threshold))}</span></div></div><p className="card-copy">{details?.baseline_semantics ?? "Contributions explain the raw estimator log-odds."} {details?.all_contributions_returned ? "All 30 feature contributions were returned." : "The returned contributions may not reconstruct the full output."}</p><ShapWaterfall baseValue={Number(details?.base_value ?? 0)} outputValue={Number(explanation.raw_decision_score ?? 0)} contributions={details?.feature_contributions ?? []} /></Card> : null}
  </>;
}
