# Mission 04 database schema

The API uses SQLAlchemy 2.x with a local SQLite file at
`data/backend/mission04.sqlite3`. Alembic upgrades are explicit through `scripts/init-db.ps1`;
the server does not silently create or delete schema. The initial schema revision is
`0001_initial_api_schema`. Foreign-key enforcement is enabled for each application connection.

| Table | Stored fields | Relationships |
|---|---|---|
| `uploads` | UUID, generated storage name, SHA-256, byte size, validated row count, creation time | One upload may have multiple analyses |
| `analyses` | UUID, upload, pending/running/completed/failed state, row progress, model version, aggregate JSON summary, safe failure code, timestamps | Deleting a job cascades its derived row records |
| `predictions` | UUID, source, optional analysis and row number, model/schema/calibration/policy versions, probability, risk score/tier, class, threshold/status, separate anomaly values, timestamp | No feature vector, CSV row, filename, or target label |
| `investigations` | UUID, optional prediction, title/reason, workflow status, manually recorded outcome, timestamps | Prediction deletion sets the link null |
| `investigation_notes` | UUID, investigation, bounded note text, timestamp | Deleted with its investigation |
| `investigation_events` | UUID, investigation, event type, old/new workflow values, timestamp | Append-only events, deleted with investigation |

No user identity is asserted because this local version has no authentication. An investigation
outcome is analyst-entered workflow metadata and is not treated as verified dataset ground truth.
Notes and reasons are user-authored and may contain sensitive information; this local database is
not encrypted at rest.

Analysis results retain only derived row outputs for paginated review. Deleting an analysis removes
those rows; its upload is removed only when no other analysis uses it. Upload files otherwise expire
after the configured retention period (24 hours by default). Back up or remove the ignored local
database explicitly; the initial migration intentionally refuses a destructive downgrade.
