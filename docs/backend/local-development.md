# Local Mission 04 development

Use Windows PowerShell with Python 3.11 from the project root. Install the locked environment if
needed, then initialize the schema and start one loopback server:

```powershell
.\scripts\setup.ps1
.\scripts\init-db.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'
.\scripts\start-api.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'
```

The start script applies the explicit Alembic upgrade before launching Uvicorn at
`http://127.0.0.1:8000`. `FRAUD_API_*` settings can override local paths and positive limits. The
host remains loopback-only. Copy `.env.example` to an ignored `.env` for local overrides. Default
data lives under ignored `data/backend/` and `data/uploads/`.
Do not put secrets, raw data, model binaries, database files, or upload content in Git.

The API loads one frozen Mission 02 classifier, one separate anomaly model, the checked Mission 03
risk policy/reference, a deterministic 512-row training-only SHAP background, and the precomputed
global validation summary. Startup verifies manifest hashes and cross-version provenance. It does
not open the source CSV or rebuild reports.

Use `scripts/verify-api-artifacts.ps1` to check manifests and local ignored artifacts,
`scripts/run-api-checks.ps1` for focused synthetic API tests/lint/format, and
`scripts/smoke-api.ps1` for a temporary loopback server exercised with real HTTPX requests. The
full project validation remains `scripts/run-checks.ps1 -PythonPath ...`.
