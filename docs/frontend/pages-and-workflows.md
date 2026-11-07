# Mission 05 pages and workflows

## Overview

Reads a bounded history page, the latest analyses page, and up to 100 open investigations. It
shows API-backed totals and explicitly labels page-derived flagged/tier counts. Empty state links
to the first prediction or CSV upload. Analysis summaries distinguish outputs from confirmed fraud.

## Prediction lab

Single mode provides required Time and Amount fields plus searchable, grouped V1–V28 inputs. The
explicit zero-filled helper is labeled as a placeholder, not an observed transaction. Batch mode
accepts bounded JSON vectors and supports client-side filtering by returned tier and sorting by
probability or risk score. The page shows probability, display score, frozen decision, tier, policy
version, model version, and the separate anomaly signal. Local explanations use the complete set of
30 returned contributions to show a cumulative raw-log-odds waterfall. Inputs must be re-supplied
for explanation because backend history does not retain features.

## CSV analysis and detail

The CSV page reads server upload limits, accepts a feature-only CSV through a file picker or
drag-and-drop, and provides a downloadable header-only template in the exact backend order. It
uploads to the local API, displays the server-computed SHA-256 and row count, then requires an
explicit action to start synchronous analysis. Recent analyses link to detail. Detail shows
returned summary fields and retrieves at most 50 derived rows per page. Delete is guarded by a
native confirmation dialog.

## Transactions and risk

History supports risk tier, timestamp range, model version, analysis ID, and sort order filters.
Record details contain only persisted derived fields and can create a linked investigation. Risk
intelligence reads the persisted policy, offers a persisted single score, and ranks an explicit
bounded input set by Top-K or percentage budget. The API's budget ceiling behavior is preserved.

## Explainability and anomalies

The global page identifies the precomputed validation partition and plots mean absolute SHAP
magnitude with an equivalent screen-reader data table. Local explanations show the backend's
raw-log-odds baseline, all signed feature contributions, model output, and reconstruction residual
in a cumulative waterfall with an equivalent data table. Anomaly review requests one or more
feature vectors and displays the anomaly score, reference percentile, and returned category without
a probability scale.

## Investigations and system

Investigations support list filtering/pagination, optional prediction linking, detail, API-allowed
status changes, analyst-recorded outcomes, append-only notes, and event history. The UI identifies
manual outcomes as non-ground-truth. System status reads liveness, readiness, model metadata, and
capabilities. It does not claim an analyst identity, production monitoring, or remote deployment.
