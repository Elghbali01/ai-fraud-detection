"use client";

import Link from "next/link";
import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { formatDate, formatNumber, formatProbability } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import type { Analysis, PageResponse, UploadResponse } from "@/lib/types";
import { Button, Card, CardHeading, EmptyState, ErrorState, PageHeader, SectionHeading } from "@/components/ui";
import { FEATURE_COLUMNS } from "@/lib/types";

interface Capabilities { max_csv_bytes?: number; max_csv_rows?: number; input_features?: string[] }

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function CsvPage() {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<UploadResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const capabilities = useApi<Capabilities>("/models/capabilities");
  const history = useApi<PageResponse<Analysis>>("/analyses?limit=20&offset=0");
  const maxBytes = capabilities.data?.max_csv_bytes;
  const maxRows = capabilities.data?.max_csv_rows;

  function selectFile(selected: File | null) {
    setUpload(null); setError(""); setFile(selected);
    if (selected && !selected.name.toLowerCase().endsWith(".csv")) setError("Select a .csv file encoded as UTF-8 with comma delimiters.");
    else if (selected && maxBytes && selected.size > maxBytes) setError(`File is larger than the current API limit (${formatBytes(maxBytes)}).`);
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0] ?? null);
  }

  function dropFile(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files?.[0] ?? null);
  }

  function downloadHeaderTemplate() {
    const file = new Blob([`${FEATURE_COLUMNS.join(",")}\n`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(file);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "fraud-feature-template.csv";
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  async function uploadFile() {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) { setError("Select a .csv file."); return; }
    if (maxBytes && file.size > maxBytes) { setError(`File is larger than the current API limit (${formatBytes(maxBytes)}).`); return; }
    setBusy(true); setError(""); setUpload(null);
    const body = new FormData(); body.append("file", file, file.name);
    try { setUpload(await apiRequest<UploadResponse>("/uploads/csv", { method: "POST", body })); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "CSV upload failed."); }
    finally { setBusy(false); }
  }

  async function createAnalysis() {
    if (!upload) return;
    setBusy(true); setError("");
    try {
      const analysis = await apiRequest<Analysis>("/analyses", { method: "POST", body: JSON.stringify({ upload_id: upload.upload_id }) });
      router.push(`/analyses/${analysis.analysis_id}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Analysis could not be created."); }
    finally { setBusy(false); }
  }

  return <>
    <PageHeader eyebrow="Workspace / file analysis" title="CSV analysis" description="Upload a feature-only CSV, validate its exact schema, then score it through the synchronous Mission 04 analysis workflow. Results are paginated and contain derived outputs only." />
    <div className="grid grid-main-side">
      <Card className="card-pad">
        <CardHeading title="Start an analysis" description="The API validates file encoding, columns, size and row limits before analysis." />
        <input ref={fileInput} className="file-input" type="file" accept=".csv,text/csv" aria-label="Choose feature-only CSV" onChange={chooseFile} />
        <button className={`file-drop ${dragging ? "dragging" : ""}`} type="button" onClick={() => fileInput.current?.click()} onDragEnter={(event) => { event.preventDefault(); setDragging(true); }} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false); }} onDrop={dropFile} aria-describedby="csv-guidance">
          <span className="empty-icon"><span aria-hidden="true">⇧</span></span>
          <strong>{file ? file.name : "Choose a feature-only CSV"}</strong>
          <span>{file ? `${formatBytes(file.size)} · ${file.type || "CSV file"}` : "Drop a CSV here or browse · UTF-8, comma-delimited · exactly 30 numeric features"}</span>
          <span className="button button-default">Browse files</span>
        </button>
        <p id="csv-guidance" className="field-hint" style={{ marginTop: 10 }}>Required columns: Time, V1–V28, Amount. Do not include the Class label. No merchant or customer columns are supported.</p>
        <div className="form-actions"><Button type="button" icon="file" onClick={downloadHeaderTemplate}>Download CSV header template</Button><span className="field-hint">Header only; no sample transaction values.</span></div>
        {file && !error ? <div className="callout" style={{ marginTop: 13 }}><span aria-hidden="true">✓</span><div><strong>{file.name}</strong> is selected. It will be sent to the local API only after you choose Upload.</div></div> : null}
        {error ? <p className="form-error" role="alert" style={{ marginTop: 12 }}>{error}</p> : null}
        <div className="form-actions" style={{ marginTop: 14 }}><Button variant="primary" icon="upload" disabled={!file || busy || Boolean(error)} onClick={uploadFile}>{busy ? "Uploading…" : "Upload and validate"}</Button>{file ? <Button variant="quiet" onClick={() => { setFile(null); setUpload(null); setError(""); if (fileInput.current) fileInput.current.value = ""; }}>Clear selection</Button> : null}</div>
        {upload ? <div className="stack-sm" style={{ marginTop: 15 }}><div className="kv-grid"><div className="kv"><span className="kv-label">Validated rows</span><span className="kv-value">{formatNumber(upload.row_count, 0)}</span></div><div className="kv"><span className="kv-label">File size</span><span className="kv-value">{formatBytes(upload.size_bytes)}</span></div><div className="kv"><span className="kv-label">Schema version</span><span className="kv-value">{upload.schema_version}</span></div><div className="kv"><span className="kv-label">SHA-256</span><span className="kv-value mono" style={{ fontSize: 9 }}>{upload.sha256}</span></div></div><Button variant="primary" icon="chart" disabled={busy} onClick={createAnalysis}>{busy ? "Analyzing…" : "Create analysis"}</Button></div> : null}
      </Card>
      <div className="stack">
        <Card className="card-pad"><CardHeading title="Input limits" description="Limits are read from the backend capability endpoint." />{capabilities.error ? <ErrorState error={capabilities.error} onRetry={capabilities.refresh} /> : capabilities.loading ? <div className="skeleton" /> : <div className="kv-grid"><div className="kv"><span className="kv-label">Maximum upload</span><span className="kv-value">{maxBytes ? formatBytes(maxBytes) : "—"}</span></div><div className="kv"><span className="kv-label">Maximum rows</span><span className="kv-value">{maxRows ? formatNumber(maxRows, 0) : "—"}</span></div></div>}</Card>
        <div className="callout callout-warning"><span aria-hidden="true">!</span><div><strong>Synchronous scoring.</strong> A successful request finishes the analysis in the API process. A restart will fail an interrupted job; it does not resume it.</div></div>
        <div className="callout"><span aria-hidden="true">i</span><div>Uploaded feature values are not stored in prediction history. The API persists derived scores and expiring upload metadata/files according to its local retention policy.</div></div>
      </div>
    </div>

    <SectionHeading title="Recent analyses" description="The latest 20 saved jobs returned by the local API." meta={history.data ? `${history.data.count} SHOWN` : undefined} />
    <Card className="card-pad">
      {history.error ? <ErrorState error={history.error} onRetry={history.refresh} /> : history.loading ? <div className="loading-surface"><div className="skeleton" /><div className="skeleton" /></div> : (history.data?.analyses ?? []).length ? <div className="stack-sm">{history.data!.analyses!.map((analysis) => <Link className="analysis-card" href={`/analyses/${analysis.analysis_id}`} key={analysis.analysis_id}><div><h3>{formatNumber(analysis.processed_rows, 0)} of {formatNumber(analysis.requested_rows, 0)} rows processed</h3><p>{formatDate(analysis.created_at)} · {analysis.analysis_id}</p><div className="analysis-card-meta"><span className={`badge ${analysis.status === "completed" ? "tone-success" : analysis.status === "failed" ? "tone-danger" : "tone-warning"}`}>{analysis.status}</span>{analysis.summary ? <span className="badge">{formatProbability((analysis.summary.flagged_percentage ?? 0) / 100)} flagged for review</span> : null}{analysis.model_version ? <span className="badge">{analysis.model_version}</span> : null}</div></div><span className="button button-default">View results →</span></Link>)}</div> : <EmptyState icon="file" title="No saved analyses" description="Validated uploads appear here after you explicitly start analysis." />}
      <div className="footer-note">Summaries for unlabeled uploads contain score distributions and review counts only. The backend does not compute precision, recall, or other label-based metrics for these files.</div>
    </Card>
  </>;
}
