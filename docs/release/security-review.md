# Mission 06 security review

**Review date:** 2026-11-07
**Boundary:** local development and portfolio demonstration; no production approval is implied.

## Implemented controls

- API and demo frontend bind to `127.0.0.1`. The demo launcher checks both loopback ports before
  starting and refuses an occupied port without terminating its owner.
- CORS origins are explicit local frontend origins; wildcard origins with credentials are not used.
  CORS is not authentication.
- API defaults cap JSON bodies at 2 MiB, CSV uploads at 32 MiB and 20,000 rows, inference batches at
  1,000 rows, explanation batches at 25, and API page size at 100.
- Feature inputs require the exact 30-column schema and finite numeric values. CSV files use a
  server-generated name, exact feature-only headers, bounded streamed size/row count, and a default
  24-hour upload retention period.
- Prediction history persists derived outputs without the submitted feature vector. The separate
  local SQLite database is not encrypted at rest.
- Model and SHAP artifacts are manifest-pinned and checksum-verified before the service becomes
  ready. User uploads are never deserialized as Python/model objects.
- API errors are sanitized and carry request IDs. SQLite schema version is checked at startup;
  foreign keys and transaction scopes are used for persisted workflows.
- The Next.js proxy adds a per-request script nonce, `strict-dynamic`, a local API `connect-src`,
  `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, and `frame-ancestors 'none'`. The
  production script policy does not include `unsafe-eval`. `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy` are set. `style-src 'unsafe-inline'`
  remains necessary for current React inline styles and is a known CSP relaxation.
- The demo stop helper verifies recorded PID, executable path, and process start time before stopping
  only the two session processes. It preserves the demo DB and uploads.

## Dependency advisory scan

Python advisory audit before corrections reported 103 advisory records in three installed packages
(Pillow 12.1.1, Tornado 6.5.4, setuptools 65.5.0). The active `requirements-mission04.lock` and
build-system bound were updated to Pillow 13.0.0, Tornado 6.6, and setuptools 84.1.0. A new scan
checked 111 installed packages and reported **zero known vulnerabilities**; `pip check` found no
broken requirements.

The full npm audit examined 522 dependency nodes: 20 production, 465 development, 86 optional, and
8 peer dependencies. It reported **10 moderate findings in development tooling** and no high or
critical findings. All findings trace to `minimatch` 10.2.6 and
[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249). A separate
`npm audit --omit=dev` reported **zero vulnerabilities** across production dependencies. npm's
offered full-tree fix downgraded `eslint-config-next` to 15.5.29 while this project uses Next.js
16.4.5; that mismatched downgrade was not applied. The current ESLint/Next toolchain passes lint,
typecheck, tests, build, and browser regression. The moderate development-only advisory remains a
tracked toolchain maintenance item.

## Remaining security risks

- The API has no authentication, authorization, analyst identity, or multi-user case ownership.
- Loopback binding is a local-network exposure boundary, not a substitute for authentication or OS
  user separation. Do not bind to all interfaces or deploy this API publicly.
- SQLite and local uploads are not encrypted at rest. Investigation notes may contain analyst text.
- There is no production session/CSRF design, centralized audit service, secret-management system,
  external alert delivery, WAF, centralized monitoring, or incident-response process.
- Local joblib artifacts are trusted inputs. Continue to verify their checksums and do not load
  artifacts from untrusted sources.
- No external penetration test or production threat model was performed.

Before any shared or network deployment, add and test authentication/authorization, encrypted and
retained storage, per-user audit controls, rate limiting, secret management, observability, and an
independent security review. This application remains a local portfolio demo.
