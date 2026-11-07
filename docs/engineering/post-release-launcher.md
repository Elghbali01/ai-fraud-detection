# Post-release one-click Windows launcher

## Startup and shutdown design

`START_AI_FRAUD.bat` runs `scripts/start-one-click.ps1` through Windows PowerShell 5.1 with
`-ExecutionPolicy Bypass` scoped to that child process. It does not alter an execution-policy scope,
request elevation, install dependencies, retrain the model, or modify scientific outputs. The
orchestrator reuses `scripts/start-demo.ps1`; it does not create a second API/frontend runtime.

The launcher defaults to the verified Mission 06 production bundle and loopback ports **8001** for
FastAPI and **3100** for Next.js. It checks Python 3.11, Node.js 20.9+, installed Python/Next.js
dependencies, the configured production bundle, local model artifacts, and port availability. It
initializes or confirms the existing migration through the project's database initializer, then
starts FastAPI and waits for `/api/v1/ready` plus `/api/v1/health` to confirm the database and model.
Only then does it start Next.js and wait for HTTP 200 with the dashboard marker. It opens the
dashboard URL through the Windows default URL handler only after both services pass.

An exclusive local start lock serializes double-clicks. A healthy session manifest is checked against
PID, executable path, process start time, and live endpoints; a second start reuses that session
instead of starting duplicate services. Session manifests, logs, and the lock live under ignored
`data/backend/`. Timestamped launcher, API, and frontend logs are stored in
`data/backend/mission06-demo-logs/`.

`STOP_AI_FRAUD.bat` calls `scripts/stop-demo.ps1`. With no session argument, the script discovers
the project's recorded session files. Before stopping anything, it checks the project root, PID,
executable, and start time. It then terminates only the process handles matching those identities,
removes the session manifest, and appends stop events to the local log. It never terminates every
Python or Node process, and it preserves SQLite, model artifacts, uploads, and source data. A second
stop with no manifest reports that the app is already stopped.

## Local validation record

**Environment:** Windows 11 build 26200; Windows PowerShell 5.1.26100.8972 and PowerShell 7.6.9;
Python 3.11.8; Node.js 20.19.6; Next.js 16.4.5.

- PowerShell parser checks passed for `start-one-click.ps1`, `start-demo.ps1`, and `stop-demo.ps1`
  under both PowerShell 5.1 and PowerShell 7. The incompatible `Get-Date -AsUTC` use was replaced
  with `(Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")`.
- A complete direct launch and safe stop also passed under PowerShell 7. The first PowerShell 7
  smoke exposed a null `Get-Process.Path` value; CIM access is unavailable in this environment, so
  process identity lookup now falls back to the process handle's `MainModule.FileName` before CIM.
  The frontend-start error path now safely stops a launched frontend as well as the API. The
  rerun reached full readiness and the PowerShell 7 stop script stopped only its recorded PIDs.
- `cmd.exe /d /c START_AI_FRAUD.bat < NUL` executed the actual root batch file through its
  PowerShell 5.1 child and reached the READY summary after live endpoint checks. This was a CMD
  invocation, not an Explorer double-click. Because the non-interactive harness could not press the
  batch file's final `pause`, that exact test harness was closed after verifying its process identity.
- The full startup reported API PID **31432**, frontend PID **38312**, SQLite migration
  `0002_prediction_semantics`, and model
  `mission02:m02-20261106T185430319319Z-logistic_balanced_c1-3547d288`. The readiness endpoint
  confirmed the frozen artifacts and database; the frontend returned HTTP 200 and contained the
  expected dashboard marker.
- A second PowerShell 5.1 launch found the same ready session and reused PIDs 31432/38312. The
  browser action was intercepted only for this repeat-launch test; no second service process was
  created.
- The actual `STOP_AI_FRAUD.bat` stopped those two recorded processes. A second run reported the
  application already stopped. No other existing Node processes were terminated.
- The successful PowerShell 7 run reported API PID **19980** and frontend PID **25524**, verified
  the same database revision/model version, and returned HTTP 200 with the dashboard marker. The
  default URL handler was invoked; `stop-demo.ps1` then safely stopped those two PIDs.
- A live TCP listener deliberately held port 8001. Startup logged the occupied-port error, created
  no session, and left that listener running.
- Controlled child-process failure injections verified that an early FastAPI exit was logged and
  prevented Next.js/browser startup, and that an early Next.js exit was logged and caused only the
  recorded FastAPI process to stop. No production code, model, or database was altered for these
  injections.
- Launcher/API/frontend output and errors were present under the ignored log folder. The startup
  and stop paths were exercised from CMD and Windows PowerShell; execution policy scopes remained
  unchanged.
- Before/after comparison: `mission06-demo.sqlite3` remained **102,400 bytes**, SHA-256
  `1c003c25b03efc3c7f088d8f677806c9a6c3192f6ef5944a7991ade09b05f347`. The supervised model,
  Isolation Forest artifact, SHAP background, and anomaly reference hashes were unchanged. No model
  training or data deletion occurred.

The default URL handler returned successfully for `http://127.0.0.1:3100`. The browser window and
rendered page were not visually verified in this environment, so this record does not claim an
observed browser window. The local computer-use inspection helper failed to initialize because its
kernel-assets directory was unavailable. The UI itself was confirmed ready via HTTP.

The app remains a local-only demonstration. Port conflicts are reported without stopping the owning
application. Missing dependencies or an incorrect production API URL produce a logged error; the
launcher does not auto-install packages or rebuild the frontend.
