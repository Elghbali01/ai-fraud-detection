"""Exercise the running local API through real HTTP using synthetic inputs only."""

from __future__ import annotations

import argparse
import csv
import io
import json
import statistics
import time

import httpx

from fraud_detection.schema import FEATURE_COLUMNS


def require(response: httpx.Response, status: int = 200) -> dict:
    if response.status_code != status:
        raise AssertionError(
            f"{response.request.method} {response.request.url.path} returned "
            f"{response.status_code}: {response.text[:300]}"
        )
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    with httpx.Client(base_url=base, timeout=90, trust_env=False) as client:
        deadline = time.monotonic() + 120
        while True:
            try:
                health = require(client.get("/api/v1/health"))
                break
            except (httpx.HTTPError, AssertionError) as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "The local API did not become healthy within 120 seconds"
                    ) from exc
                time.sleep(0.5)
        assert health["status"] == "alive"
        assert health["components"]["process"] == "alive"
        assert health["components"]["models"] == "available"
        ready = require(client.get("/api/v1/ready"))
        model = require(client.get("/api/v1/models/current"))
        capabilities = require(client.get("/api/v1/models/capabilities"))
        assert ready["model_version"] == model["model_version"]
        assert capabilities["feature_count"] == 30
        assert model["threshold"] > 0

        features = {name: 0.0 for name in FEATURE_COLUMNS}
        prediction = require(client.post("/api/v1/predictions", json=features))
        assert prediction["model_version"] == model["model_version"]
        assert prediction["timestamp"].endswith(("+00:00", "Z"))
        assert prediction["anomaly"]["score_is_probability"] is False
        require(client.post("/api/v1/risk/score", json=features))
        batch = require(
            client.post(
                "/api/v1/predictions/batch",
                json={"transactions": [features, features]},
            )
        )
        assert batch["count"] == 2
        priority = require(
            client.post(
                "/api/v1/risk/prioritize",
                json={"transactions": [features], "budget_percentage": 1},
            )
        )
        assert priority["selected_count"] == 1
        require(client.post("/api/v1/anomalies/score", json={"transactions": [features]}))
        policy = require(client.get("/api/v1/risk/policy"))
        assert policy["policy_version"] == model["risk_policy_version"]

        linear = require(
            client.post(
                "/api/v1/explanations/local",
                json={"features": features, "method": "linear_log_odds", "top_n": 30},
            )
        )
        assert linear["explanation"]["output_space"] == "raw_log_odds"
        shap = require(
            client.post(
                "/api/v1/explanations/local",
                json={
                    "features": features,
                    "method": "shap_interventional_log_odds",
                    "top_n": 30,
                },
            )
        )
        assert shap["explanation"]["reconstruction_error"] < 1e-6
        global_summary = require(client.get("/api/v1/explanations/global"))
        assert global_summary["output_space"] == "raw_log_odds"
        assert len(global_summary["features"]) == 30
        require(client.get("/openapi.json"))

        invalid = client.post("/api/v1/predictions", json={**features, "Class": 0})
        require(invalid, 422)
        assert "Class" not in invalid.text
        assert invalid.json()["timestamp"]
        unsupported = client.post(
            "/api/v1/uploads/csv",
            files={"file": ("wrong.txt", b"not a csv", "text/plain")},
        )
        require(unsupported, 415)

        content = io.StringIO()
        writer = csv.DictWriter(content, fieldnames=list(FEATURE_COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerow(features)
        writer.writerow({name: 0.1 for name in FEATURE_COLUMNS})
        uploaded = require(
            client.post(
                "/api/v1/uploads/csv",
                files={
                    "file": (
                        "arbitrary-client-filename.csv",
                        content.getvalue().encode(),
                        "text/csv",
                    )
                },
            )
        )
        assert uploaded["row_count"] == 2
        analysis = require(
            client.post("/api/v1/analyses", json={"upload_id": uploaded["upload_id"]})
        )
        assert analysis["status"] == "completed"
        assert analysis["summary"]["labels_present"] is False
        assert analysis["summary"]["flagged_percentage"] >= 0
        analysis_id = analysis["analysis_id"]
        require(client.get("/api/v1/analyses"))
        require(client.get(f"/api/v1/analyses/{analysis_id}"))
        require(client.get(f"/api/v1/analyses/{analysis_id}/summary"))
        results = require(client.get(f"/api/v1/analyses/{analysis_id}/results"))
        assert results["count"] == 2
        assert "features" not in results["results"][0]

        history = require(client.get("/api/v1/history"))
        assert history["total"] >= 4
        require(client.get(f"/api/v1/history/{prediction['record_id']}"))
        investigation = require(
            client.post(
                "/api/v1/investigations",
                json={
                    "prediction_id": prediction["record_id"],
                    "title": "Local smoke review",
                    "reason": "Synthetic HTTP smoke test",
                },
            )
        )
        investigation_id = investigation["investigation_id"]
        require(client.get("/api/v1/investigations"))
        require(
            client.patch(
                f"/api/v1/investigations/{investigation_id}",
                json={"status": "In Review", "outcome": "Unconfirmed"},
            )
        )
        require(
            client.post(
                f"/api/v1/investigations/{investigation_id}/notes",
                json={"body": "Synthetic HTTP workflow note."},
            )
        )
        investigation_detail = require(client.get(f"/api/v1/investigations/{investigation_id}"))
        assert len(investigation_detail["notes"]) == 1
        deleted = require(client.delete(f"/api/v1/analyses/{analysis_id}"))
        assert deleted["deleted"] is True

        latency_ms = []
        for _ in range(10):
            start = time.perf_counter()
            require(client.post("/api/v1/predictions", json=features))
            latency_ms.append((time.perf_counter() - start) * 1_000)
        ordered = sorted(latency_ms)
        p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
        print(
            json.dumps(
                {
                    "live_http_smoke": "passed",
                    "verified_endpoint_operations": 30,
                    "synthetic_prediction_latency_ms": {
                        "median": round(statistics.median(latency_ms), 3),
                        "p95": round(p95, 3),
                        "samples": len(latency_ms),
                    },
                    "notebook_data_or_final_test_rows_used": False,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
