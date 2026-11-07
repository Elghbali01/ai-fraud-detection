"use client";

import { useApi, type ApiResource } from "@/lib/use-api";
import type { ReactNode } from "react";
import { formatNumber, formatProbability } from "@/lib/format";
import type { HealthResponse, ReadyResponse } from "@/lib/types";
import { Button, Callout, Card, CardHeading, PageHeader, StatusLine } from "@/components/ui";

interface ModelInfo { model_version?: string; model_type?: string; decision_threshold?: number; threshold?: number; calibration_method?: string; probability_calibration_status?: string; risk_policy_version?: string; [key: string]: unknown }
interface Capabilities { max_batch_rows?: number; max_explanation_batch?: number; max_csv_bytes?: number; max_csv_rows?: number; max_concurrent_analyses?: number; [key: string]: unknown }

function ValueList({ value }: { value: Record<string, unknown> }) {
  return <div className="kv-grid">{Object.entries(value).map(([key, entry]) => <div className="kv" key={key}><span className="kv-label">{key.replaceAll("_", " ")}</span><span className="kv-value">{typeof entry === "object" && entry !== null ? JSON.stringify(entry) : String(entry)}</span></div>)}</div>;
}

function EndpointCard<T>({ title, description, resource, children }: { title: string; description: string; resource: ApiResource<T>; children?: (data: T) => ReactNode }) {
  return <Card className="card-pad"><CardHeading title={title} description={description} action={<Button icon="refresh" onClick={resource.refresh}>Refresh</Button>} />{resource.error ? <div className="error-state" role="alert"><div><h3>Endpoint unavailable</h3><p>{resource.error.message}</p></div></div> : resource.loading ? <div className="loading-surface"><div className="skeleton" /><div className="skeleton" /></div> : resource.data ? children ? children(resource.data) : <ValueList value={resource.data as unknown as Record<string, unknown>} /> : null}</Card>;
}

export function SystemPage() {
  const health = useApi<HealthResponse>("/health");
  const ready = useApi<ReadyResponse>("/ready");
  const model = useApi<ModelInfo>("/models/current");
  const capabilities = useApi<Capabilities>("/models/capabilities");
  return <>
    <PageHeader eyebrow="Operations / runtime" title="Model & system" description="Health, readiness, frozen model metadata and request limits are read from the local Mission 04 API. This page does not claim production monitoring or external deployment." />
    <div className="grid grid-2">
      <EndpointCard title="Process health" description="GET /api/v1/health · liveness plus safe component states." resource={health}>{(data) => <><div className="kv-grid" style={{ marginBottom: 12 }}><div className="kv"><span className="kv-label">Service status</span><span className="kv-value">{data.status}</span></div><div className="kv"><span className="kv-label">API version</span><span className="kv-value">{data.api_version}</span></div></div><div className="stack-sm">{Object.entries(data.components).map(([name, state]) => <div className="analysis-card" key={name}><span className="kv-label">{name.replaceAll("_", " ")}</span><StatusLine state={state === "available" || state === "alive" ? "online" : "offline"} label={state} /></div>)}</div></>}</EndpointCard>
      <EndpointCard title="Readiness" description="GET /api/v1/ready · checks the verified runtime and migrated database." resource={ready}>{(data) => <div className="stack-sm"><div className="callout"><span aria-hidden="true">✓</span><div><strong>API ready.</strong> The backend confirms its model artifacts, explanation/anomaly services and schema-migrated SQLite database are available.</div></div><div className="kv"><span className="kv-label">Active model version</span><span className="kv-value">{data.model_version}</span></div></div>}</EndpointCard>
    </div>
    <div className="grid grid-2" style={{ marginTop: 14 }}>
      <EndpointCard title="Current model metadata" description="GET /api/v1/models/current · frozen Mission 02/03 runtime." resource={model}>{(data) => <><div className="kv-grid" style={{ marginBottom: 12 }}><div className="kv"><span className="kv-label">Model version</span><span className="kv-value">{data.model_version ?? "—"}</span></div><div className="kv"><span className="kv-label">Decision threshold</span><span className="kv-value">{formatProbability(data.decision_threshold ?? data.threshold)}</span></div><div className="kv"><span className="kv-label">Model type</span><span className="kv-value">{String(data.model_type ?? "—")}</span></div><div className="kv"><span className="kv-label">Calibration</span><span className="kv-value">{String(data.probability_calibration_status ?? data.calibration_method ?? "—")}</span></div></div><details><summary className="field-label" style={{ cursor: "pointer" }}>Inspect full safe response</summary><pre className="json-pre">{JSON.stringify(data, null, 2)}</pre></details><div className="footer-note">Threshold metadata is historical frozen configuration. It is not a claim that current transaction outcomes were independently evaluated.</div></>}</EndpointCard>
      <EndpointCard title="Capabilities and limits" description="GET /api/v1/models/capabilities · server-provided bounds." resource={capabilities}>{(data) => <><div className="kv-grid">{Object.entries(data).map(([key, value]) => <div className="kv" key={key}><span className="kv-label">{key.replaceAll("_", " ")}</span><span className="kv-value">{typeof value === "number" ? formatNumber(value, 0) : String(value)}</span></div>)}</div><div className="footer-note">Limits can change with local settings; client forms defer to these values where exposed.</div></>}</EndpointCard>
    </div>
    <div className="grid grid-2" style={{ marginTop: 14 }}><Callout tone="warning" icon="alert"><strong>Trusted local workflow only.</strong> The API has no authentication. CORS is not an access-control boundary. Keep both services loopback-only and do not expose them to a network.</Callout><Callout tone="warning" icon="alert"><strong>Scientific constraints.</strong> ULB data is historical, PCA feature names are anonymized, the final-test partition is consumed, and the model has not been validated against current real-world fraud costs.</Callout></div>
  </>;
}
