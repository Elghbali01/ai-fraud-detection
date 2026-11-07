# Mission 06 architecture and data flows

These diagrams describe the implemented local application. Training is an offline, completed workflow; API requests load verified artifacts and do not retrain or read the raw ULB dataset.

## System architecture

```mermaid
flowchart LR
  ULB[Verified ULB CSV<br/>local, ignored] --> INGEST[Schema validation and EDA]
  INGEST --> EDA[EDA reports and figures]
  ULB --> TRAIN[Mission 02 temporal training and validation]
  TRAIN --> ARTIFACTS[Frozen supervised and anomaly artifacts<br/>local, ignored]
  ARTIFACTS --> SERVICES[Mission 03 inference, SHAP, risk, anomaly services]
  SERVICES --> API[FastAPI v1<br/>127.0.0.1]
  BROWSER[Next.js analyst UI<br/>127.0.0.1] <--> API
  API <--> SQLITE[(SQLite<br/>derived scores and analyst workflow)]
  SYNTH[Synthetic feature-only demo CSV] --> BROWSER
```

The UI submits exact feature vectors to the API. SQLite stores derived prediction fields, analysis summaries/results, upload metadata, and investigation activity. Submitted feature values are not stored in prediction history. Raw source data, trained model binaries, and local runtime databases remain outside Git.

## Single prediction

```mermaid
sequenceDiagram
  actor Analyst
  participant UI as Next.js UI
  participant API as FastAPI v1
  participant Schema as Feature contract
  participant Model as Frozen Mission 02 model
  participant Risk as Mission 03 risk and anomaly services
  participant DB as SQLite
  Analyst->>UI: Enter 30 finite feature values
  UI->>API: POST prediction request
  API->>Schema: Validate exact names and values
  Schema-->>API: Valid feature vector
  API->>Model: Calibrated inference
  Model-->>API: Fraud probability and threshold decision
  API->>Risk: Risk tier and separate anomaly signal
  Risk-->>API: Policy version, tier, anomaly score
  API->>DB: Persist derived outputs only
  DB-->>API: Record identifier
  API-->>UI: Typed prediction response
  UI-->>Analyst: Probability, policy decision, tier, anomaly
```

The decision threshold is frozen at `0.1835921396957453`. A predicted flag is a review signal, not a confirmed-fraud label. Anomaly scores are not probabilities and are never blended into the classifier probability.

## Feature-only CSV analysis

```mermaid
flowchart LR
  FILE[CSV file] --> UPLOAD[Bounded upload and exact schema validation]
  UPLOAD --> META[Server-generated upload metadata]
  UPLOAD --> ANALYZE[Synchronous bounded analysis]
  ARTIFACTS[Verified inference artifacts] --> ANALYZE
  ANALYZE --> RESULTS[Derived per-row results and aggregates]
  RESULTS --> DB[(SQLite analyses and predictions)]
  DB --> PAGE[Paginated API results]
  PAGE --> UI[CSV results page]
  UI --> DELETE[Explicit analysis deletion]
  DELETE --> DB
```

The API enforces a 32 MiB upload cap and 20,000-row cap by default, validates the feature-only schema, assigns a server-generated filename, and expires uploads after 24 hours. CSV output is a prediction workflow, not an evaluation against labels. The synthetic fixture has 30 rows and no target column.

## Explainability

```mermaid
flowchart LR
  LOCAL[Validated feature vector] --> LOCALSVC[Local SHAP service]
  BG[Verified training-only SHAP background] --> LOCALSVC
  LOCALSVC --> LOCALOUT[Raw log-odds contributions]
  GLOBAL[Verified global summary artifact] --> GLOBALSVC[Global explanation endpoint]
  GLOBALSVC --> GLOBALOUT[Validation-time global summary]
  LOCALOUT --> UI[Explanation UI and data table]
  GLOBALOUT --> UI
```

Local and global explanation values are raw log-odds contributions. They are not percentage-point changes in the later calibrated fraud probability and are not causal explanations. Global attribution is based on the persisted development-time summary; it is not recomputed from the final-test partition.

## SQLite persistence

```mermaid
flowchart TB
  ROUTES[Prediction, CSV, history, investigation routes] --> SESSION[SQLAlchemy session]
  SESSION --> TX[SQLite transaction]
  TX --> UPLOADS[uploads metadata]
  TX --> ANALYSES[analyses and aggregates]
  TX --> PREDICTIONS[predictions: derived fields only]
  TX --> CASES[investigations]
  CASES --> NOTES[investigation_notes]
  CASES --> EVENTS[investigation_events]
  MIGRATIONS[Alembic schema migrations] --> DB[(Local SQLite database)]
  UPLOADS --> DB
  ANALYSES --> DB
  PREDICTIONS --> DB
  NOTES --> DB
  EVENTS --> DB
```

Startup verifies Alembic revision `0002_prediction_semantics`. Foreign keys and indexes support analysis deletion, transaction history, risk-tier filters, and case lookups. A synchronous analysis interrupted by a process restart is marked failed rather than reported as completed. The database is local and not encrypted at rest.

## Investigation workflow

```mermaid
stateDiagram-v2
  [*] --> Open: create case
  Open --> InReview: analyst transition
  Open --> Escalated: analyst transition
  Open --> Closed: analyst transition
  InReview --> Open: analyst transition
  InReview --> Escalated: analyst transition
  InReview --> Closed: analyst transition
  Escalated --> InReview: analyst transition
  Escalated --> Closed: analyst transition
  Closed --> [*]
  state "Notes and workflow events append to SQLite" as Activity
  Open --> Activity
  InReview --> Activity
  Escalated --> Activity
  Closed --> Activity
```

Analyst-recorded outcomes are workflow annotations. The API does not create adjudicated ground truth or claim analyst identity.
