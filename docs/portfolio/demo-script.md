# Local portfolio demo walkthrough

**Target length:** 6–8 minutes

**Data:** explicitly synthetic feature-only inputs

**Services:** local API at `127.0.0.1:8001`, dashboard at `127.0.0.1:3100` by default.

## Before presenting

1. Build the frontend and install the project dependencies as described in the README.
2. Double-click `START_AI_FRAUD.bat`. The launcher verifies both services and opens the dashboard
   after its readiness checks pass. On the first launch, allow Windows to use the existing default
   browser association; no credentials or browser permissions are required.
3. Confirm the system page reports API readiness and the frozen
   model version.
4. Use only synthetic feature values and
   `docs/portfolio/fixtures/synthetic-demo-transactions.csv`. The file contains 30 rows and no
   target label.

## Walkthrough

### 1. System and scope — about 45 seconds

Start on the dashboard, then open system/model status. Explain that the UI calls a local API which
loads checksummed model artifacts; it does not train on page load. The displayed performance is
historical research evidence, not a live production scorecard.

### 2. Single prediction — about 60 seconds

Enter a synthetic feature vector and run prediction. Point out the probability, frozen threshold
decision, risk tier, and anomaly output as separate outputs. Clarify that a flagged or unusual
transaction is a review signal and is not confirmed fraud.

### 3. Explanation — about 60 seconds

Open the local explanation. Explain that SHAP contributions are raw log-odds, not percentage-point
changes in the calibrated probability and not causal factors. Show the accompanying data table as an
accessible alternative to the visual chart.

### 4. CSV analysis — about 90 seconds

Upload the synthetic fixture, review the aggregate and paginated rows, then show that the file has no
ground-truth target column. Explain that the workflow generates estimates and is not an evaluation
against labels. Delete the analysis if time permits.

### 5. Risk and anomaly — about 60 seconds

Open prioritization and compare the alert-capacity view with the anomaly view. Risk tiers come from
the persisted validation policy; anomaly scores come from a separate Isolation Forest and are not
fraud probabilities.

### 6. Investigation semantics — about 60 seconds

Show an explicitly synthetic investigation and its status/history. Explain that an analyst outcome
is a workflow annotation; the application does not create adjudicated ground truth or capture
analyst identity.

## Close

State the limits clearly: historical anonymized data, a consumed final-test period, no independent
later cohort, no authentication, no encryption at rest, and no production deployment. The app is a
local portfolio demonstration only. See the release checklist before sharing the demo.

## Stop safely

Double-click `STOP_AI_FRAUD.bat`. The helper validates process identity and stops only the demo's
recorded processes. It preserves the SQLite database and uploaded files for the next demonstration.
