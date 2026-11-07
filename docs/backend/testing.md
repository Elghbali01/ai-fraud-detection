# Mission 04 testing and verification

Routine API tests use synthetic records and throwaway SQLite files; they do not need `creditcard.csv`
or local model binaries. Run:

```powershell
.\scripts\run-api-checks.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'
.\scripts\smoke-api.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'
```

The smoke script launches a hidden Uvicorn process on an available loopback port and uses HTTPX
over an actual TCP connection. It exercises model/health, prediction, risk, anomaly, linear/SHAP,
global explanation, multipart upload, synchronous analysis, history, investigation, deletion, and
validation error paths. It reports latency for ten synthetic prediction calls; those timings are
local smoke measurements, not production performance claims.

The opt-in integration verifies the real checksummed Mission 02/03 artifacts while sending only
synthetic zero-valued feature vectors:

```powershell
$env:RUN_MISSION04_ARTIFACT_TESTS = '1'
& .\.venv-isolated\Scripts\python.exe -m pytest -m mission04_real_artifacts -q
Remove-Item Env:RUN_MISSION04_ARTIFACT_TESTS -ErrorAction SilentlyContinue
```

It does not read or score rows from the ULB CSV, including the consumed final-test partition.
The full `scripts/run-checks.ps1` validates project tests, Ruff, formatting, compilation,
notebooks, and synthetic EDA smoke. No failing test is skipped or disabled.
