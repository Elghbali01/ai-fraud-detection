# System Overview

## Project vision

The six-mission product gives financial analysts a reproducible way to inspect transaction data, compare validated model outputs, review explanations, and prioritize investigation. Historical labels, predictions, risk scores, anomaly scores, and explanations are separate outputs. None is proof of fraud.

## Layer responsibilities

- Raw data boundary: local source files under data/raw, read-only for the analysis pipeline, never committed.
- Data and analytics package: src/fraud_detection handles loading, explicit schema validation, profiling, statistics, charts, and report serialization.
- Notebooks: analytical narratives import the package and display source status and interpretation limitations.
- Scripts: Windows-compatible setup, acquisition, checks, and repeatable CLI entry points.
- Reports: compact figures, tables, and summaries generated from a declared source.
- Training/evaluation: Mission 02's frozen artifacts were fit with training-only preprocessing and a chronological split; its final-test period is consumed.
- Explainability/risk: Mission 03 provides raw-log-odds explanations and separate validation-derived risk/anomaly signals.
- API: Mission 04 wraps the tested services in versioned FastAPI routes and local SQLite workflows.
- Frontend: Mission 05 consumes API contracts and labels output types clearly; Mission 06 hardened the local portfolio demo.

## Data flow

```mermaid
flowchart LR
    A[Authorized source] --> B[data/raw, ignored by Git]
    B --> C[Loader and versioned schema]
    C --> D[Quality profile]
    C --> E[Reusable EDA functions]
    D --> F[JSON and quality report]
    E --> G[Tables and figures]
    E --> H[Jupyter narratives]
    E --> I[Mission 02 training and evaluation]
    I --> J[Versioned model artifacts]
    J --> K[Mission 03 explanations and risk]
    K --> L[Mission 04 FastAPI]
    L --> M[Mission 05 Next.js analyst interface]
```

## Training versus inference

Training and evaluation are completed offline in Mission 02. The local API verifies and loads manifest-pinned artifacts at startup; inference does not train models or open the raw ULB CSV. The model version, feature contract, threshold, and checksums travel with the saved artifacts. The final-test period has been consumed and is not used for later development decisions.

## Integration and artifacts

Reusable services take DataFrames or validated schemas rather than notebook globals. Model binaries live in a local artifact store and are versioned by metadata; raw datasets and large binaries remain outside Git. The API exposes predictions, risk estimates, anomaly scores, and explanations with distinct typed fields. Mission 06 diagrams and release evidence are in [mission06-architecture.md](mission06-architecture.md) and [docs/release](../release/final-audit.md).

## Configuration

Use project configuration and explicit CLI arguments. Keep secrets in an authorized local credential store/environment, never in committed files. Avoid machine-wide settings. Seeds and time-bin parameters must be declared.

## Security and privacy

Read raw files without mutation, avoid unnecessary transaction-level exports, and keep credentials out of logs and provenance reports. Review dataset terms before redistributing any data or derived extracts. The public sample does not justify claims about customers, locations, merchants, or devices.
