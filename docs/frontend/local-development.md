# Mission 05 local development

## Prerequisites

- Windows with Node.js 20.9 or newer (the project was implemented with Node 20.19.6).
- The existing `.venv-isolated` Python environment, local Mission 02/03 artifacts, and migrated
  Mission 04 SQLite database.
- Enough disk space for one `frontend/node_modules` tree and Next.js build output. Root Git ignore
  rules exclude `node_modules`, `.next`, Playwright output, coverage, and TypeScript build info.

## Install and start

Use npm only; the frontend has one lockfile and one dependency tree:

```powershell
Set-Location frontend
npm install
Set-Location ..
```

Start the services in separate PowerShell windows:

```powershell
.\scripts\start-api.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'
.\scripts\start-frontend.ps1
```

Or start both local loopback services without duplicating a service already on its port:

```powershell
.\scripts\start-fullstack.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'
```

The default frontend is `http://127.0.0.1:3000`; the API is `http://127.0.0.1:8000`. If the
frontend port is occupied, use `-FrontendPort 3100`; the API explicitly allows this loopback
origin as an alternate local development port. Both scripts accept `-ApiPort` for local port
conflicts. The browser
calls the API directly using the explicit local CORS allowlist. Do not bind the API to a LAN IP.

## Configuration and commands

`NEXT_PUBLIC_FRAUD_API_URL` can override the browser API base URL at build/start time. It must not
contain credentials; this variable is public by design. The default is the loopback API path.

```powershell
Set-Location frontend
npm run dev
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
```

The Windows scripts run these checks from the correct package directory. Keep only one `frontend`
dependency tree; do not install a second package manager or duplicate `node_modules` at the
repository root.
