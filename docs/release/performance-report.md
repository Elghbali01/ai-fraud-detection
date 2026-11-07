# Mission 06 performance report

**Measurement date:** 2026-11-07
**Environment:** Windows 11, Python 3.11.8, Node.js 20.19.6, API on loopback port 8001, production
frontend on loopback port 3100, isolated SQLite/upload paths. Inputs were synthetic and feature-valid.

## API response observations

The measurements below are local single-process observations. They are not a load test, service-level
objective, or production latency claim.

| Operation | Request size | Observed duration |
|---|---:|---:|
| Health endpoint, 20 requests | — | median 2.77 ms; p95 3.94 ms |
| Readiness endpoint | — | median 2.50 ms |
| Single prediction, 10 requests | 30 numeric features | median 42.75 ms; p95 44.75 ms |
| Local SHAP explanation | 30 numeric features | 25.70 ms |
| Batch inference | 10 / 100 / 1,000 rows | 49.36 / 136.61 / 871.42 ms |

All bounded batch requests returned the requested number of rows. These values include local Python,
model inference, and test-server overhead; they do not imply behavior under concurrent or remote
traffic.

## Synthetic CSV observations

| Rows | Upload bytes | Upload time | Analysis time |
|---:|---:|---:|---:|
| 10 | 1,342 | 24.77 ms | 63.44 ms |
| 100 | 12,586 | 25.74 ms | 79.74 ms |
| 1,000 | 126,387 | 35.74 ms | 417.74 ms |
| 5,000 | 635,560 | 92.37 ms | 4,503.18 ms |

The 5,000-row timing shows that synchronous CSV work can occupy an API worker for several seconds.
The configured 20,000-row ceiling is an input limit, not a throughput guarantee. Larger or concurrent
workloads would need queueing/cancellation design and renewed measurement.

## Frontend build

- Optimized Next.js 16.4.5 build passed and generated 11 dynamic routes.
- The final production client build contained 19 JavaScript chunks totaling **778,604 uncompressed
  bytes**. The largest chunk was approximately **223.9 KiB**. These are raw generated file sizes,
  not compressed transfer sizes or complete page-weight measurements.
- The UI uses custom CSS/HTML visualization components rather than a charting framework.

## Limits

No controlled baseline-versus-final performance comparison, compressed network transfer test,
concurrency/throughput test, peak memory profile, cold-cache benchmark, or production hardware test
was performed. There is no measured optimization percentage or financial-impact claim. Treat the
values above as local reference observations only.
