"""Versioned local FastAPI service for the Mission 02/03 fraud model."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import threading
import time
from collections import Counter
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

import pandas as pd
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import Depends, FastAPI, File, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.config import Settings
from backend.app.core.middleware import ApiError, BodySizeLimitMiddleware, RequestIdMiddleware
from backend.app.db.dependencies import get_session
from backend.app.db.models import (
    AnalysisJob,
    Base,
    Investigation,
    PredictionRecord,
    Upload,
    new_id,
    utcnow,
)
from backend.app.db.session import make_engine, make_session_factory
from backend.app.schemas import (
    AnalysisResponse,
    ApiErrorResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    CreateAnalysisRequest,
    FeatureBatchRequest,
    FeatureInput,
    HealthResponse,
    InvestigationCreate,
    InvestigationPatch,
    LocalExplanationRequest,
    NoteCreate,
    PredictionResponse,
    PrioritizeRequest,
    ReadyResponse,
    UploadResponse,
)
from backend.app.services.artifacts import RuntimeServices, load_runtime
from backend.app.services.csv_upload import CSVValidationError, iter_csv_batches, validate_csv_file
from backend.app.services.records import (
    add_investigation_event,
    analysis_dict,
    investigation_dict,
    iso_utc,
    new_note,
    prediction_dict,
    save_prediction,
)
from fraud_detection.ml.anomaly import anomaly_scores
from fraud_detection.risk.anomaly_intelligence import anomaly_categories, anomaly_percentiles
from fraud_detection.risk.prioritization import prioritize_transactions
from fraud_detection.schema import FEATURE_COLUMNS, SCHEMA_VERSION

logger = logging.getLogger("fraud_detection.api")
SessionDependency = Annotated[Session, Depends(get_session)]
CSVFileDependency = Annotated[
    UploadFile, File(description="CSV with exactly the 30 feature columns")
]
_UUID_CSV = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.csv$")
_STATUS_TRANSITIONS = {
    "Open": {"In Review", "Escalated", "Closed"},
    "In Review": {"Open", "Escalated", "Closed"},
    "Escalated": {"In Review", "Closed"},
    "Closed": set(),
}


def _public_path(settings: Settings, storage_name: str) -> Path:
    """Resolve only server-generated UUID filenames inside the upload directory."""
    if not _UUID_CSV.fullmatch(storage_name):
        raise ApiError(404, "upload_not_found")
    directory = settings.upload_directory.resolve()
    path = (directory / storage_name).resolve()
    if path.parent != directory:
        raise ApiError(404, "upload_not_found")
    return path


def _cleanup_expired_upload_files(settings: Settings) -> None:
    """Apply the configured local file retention period to generated CSV names only."""
    directory = settings.upload_directory.resolve()
    if not directory.exists():
        return
    cutoff = time.time() - settings.upload_retention_hours * 60 * 60
    for path in directory.glob("*.csv"):
        try:
            if _UUID_CSV.fullmatch(path.name) and path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            logger.error("An expired upload file could not be removed")


async def _upload_cleanup_loop(settings: Settings) -> None:
    """Periodically expire old generated CSV files while the server is running."""
    while True:
        await asyncio.sleep(60 * 60)
        try:
            await asyncio.to_thread(_cleanup_expired_upload_files, settings)
        except OSError:
            logger.error("Upload retention cleanup failed")


def _sha256(path: Path) -> str:
    """Hash an already bounded local file in fixed-size chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime(request: Request) -> RuntimeServices:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise ApiError(503, "model_artifacts_unavailable")
    return runtime


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _feature_dict(feature: FeatureInput) -> dict[str, float]:
    return {name: float(getattr(feature, name)) for name in FEATURE_COLUMNS}


def _decorate_output(request: Request, output: dict[str, Any]) -> dict[str, Any]:
    """Attach versioned calibration and policy semantics to each model response."""
    runtime = _runtime(request)
    return {
        **output,
        "probability_calibration_status": runtime.bundle.metadata.get(
            "probability_calibration_status", "uncalibrated estimator output"
        ),
        "risk_policy_version": runtime.policy.policy_version,
    }


def _check_batch_limit(request: Request, row_count: int) -> None:
    if row_count > request.app.state.settings.max_batch_rows:
        raise ApiError(413, "batch_limit_exceeded")


def _persist_single(
    session: Session, output: dict[str, Any], *, source: str = "api"
) -> dict[str, Any]:
    record = save_prediction(session, output, source=source)
    session.commit()
    session.refresh(record)
    output = dict(output)
    output["record_id"] = record.id
    output["timestamp"] = iso_utc(record.created_at)
    return output


def _missing_analysis(session: Session, analysis_id: str) -> AnalysisJob:
    job = session.get(AnalysisJob, analysis_id)
    if job is None:
        raise ApiError(404, "analysis_not_found")
    return job


def _missing_investigation(session: Session, investigation_id: str) -> Investigation:
    item = (
        session.execute(
            select(Investigation)
            .options(joinedload(Investigation.notes), joinedload(Investigation.events))
            .where(Investigation.id == investigation_id)
        )
        .unique()
        .scalar_one_or_none()
    )
    if item is None:
        raise ApiError(404, "investigation_not_found")
    return item


def create_app(
    settings: Settings | None = None,
    *,
    runtime_override: RuntimeServices | None = None,
    engine_override: Engine | None = None,
) -> FastAPI:
    """Build an app instance; test overrides never alter the production artifact loader."""
    api_settings = settings or Settings()
    engine = engine_override or make_engine(api_settings.database_url)
    session_factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        api_settings.upload_directory.mkdir(parents=True, exist_ok=True)
        try:
            app.state.runtime = runtime_override or load_runtime(api_settings)
        except Exception:
            app.state.runtime = None
            logger.error("Trusted local API artifacts are unavailable")
        try:
            available = set(inspect(engine).get_table_names())
            expected = set(Base.metadata.tables)
            migration_config = AlembicConfig(str(api_settings.project_root / "alembic.ini"))
            latest_revision = ScriptDirectory.from_config(migration_config).get_current_head()
            with engine.connect() as connection:
                current_revision = MigrationContext.configure(connection).get_current_revision()
            app.state.database_ready = (
                expected.issubset(available) and current_revision == latest_revision
            )
        except Exception:
            app.state.database_ready = False
            logger.error("Local database migration state could not be verified")
        if app.state.database_ready:
            try:
                with session_factory() as session:
                    interrupted_jobs = session.scalars(
                        select(AnalysisJob).where(AnalysisJob.status.in_(("pending", "running")))
                    ).all()
                    for job in interrupted_jobs:
                        job.status = "failed"
                        job.failure_code = "analysis_interrupted_by_restart"
                        job.completed_at = utcnow()
                    session.commit()
            except SQLAlchemyError:
                app.state.database_ready = False
                logger.error("Interrupted analysis state could not be reconciled")
        _cleanup_expired_upload_files(api_settings)
        app.state.ready = True
        cleanup_task = asyncio.create_task(_upload_cleanup_loop(api_settings))
        try:
            yield
        finally:
            app.state.ready = False
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            if engine_override is None:
                engine.dispose()

    app = FastAPI(
        title=api_settings.app_name,
        version="1.0.0",
        description=(
            "Local-only API over the frozen Mission 02 classifier and Mission 03 risk, "
            "anomaly, and explanation artifacts. Outputs support analyst triage and do not "
            "establish fraud ground truth."
        ),
        docs_url="/docs" if api_settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if api_settings.enable_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = api_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.analysis_semaphore = threading.BoundedSemaphore(api_settings.max_concurrent_analyses)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(api_settings.cors_origins),
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    app.add_middleware(
        BodySizeLimitMiddleware,
        json_limit=api_settings.max_json_body_bytes,
        upload_limit=api_settings.max_upload_bytes,
    )
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        message = {
            "unsupported_media_type": "Upload must use a supported CSV media type.",
            "upload_limit_exceeded": "Upload exceeds the configured byte limit.",
            "invalid_history_date_range": "The from timestamp must not be later than to.",
        }.get(exc.code, exc.code.replace("_", " "))
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": message,
                "request_id": _request_id(request),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "type": str(error.get("type", "validation_error")),
                "location": str((error.get("loc") or ("request",))[0]),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": "invalid_request",
                "message": "Request validation failed.",
                "request_id": _request_id(request),
                "timestamp": datetime.now(UTC).isoformat(),
                "details": details,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {404: "not_found", 405: "method_not_allowed", 413: "request_too_large"}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": codes.get(exc.status_code, "request_error"),
                "message": "The requested operation could not be completed.",
                "request_id": _request_id(request),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        logger.error(
            "Database request failed request_id=%s error_type=%s",
            _request_id(request),
            type(_exc).__name__,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "database_unavailable",
                "message": "The local database is unavailable.",
                "request_id": _request_id(request),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, _exc: Exception) -> JSONResponse:
        logger.error("Internal API error request_id=%s", _request_id(request))
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "The request could not be completed.",
                "request_id": _request_id(request),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        schemas["ApiErrorResponse"] = ApiErrorResponse.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                response = operation.get("responses", {}).get("422")
                if response is not None:
                    response["description"] = "Request validation error"
                    response["content"] = {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ApiErrorResponse"}
                        }
                    }
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    @app.get("/api/v1/health", tags=["system"], response_model=HealthResponse)
    def health(request: Request) -> dict[str, Any]:
        """Liveness endpoint that does not expose configuration or model paths."""
        runtime = getattr(request.app.state, "runtime", None)
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
            database_status = (
                "available" if request.app.state.database_ready else "schema_unavailable"
            )
        except SQLAlchemyError:
            database_status = "unavailable"
        return {
            "status": "alive",
            "service": "fraud-risk-api",
            "api_version": "1.0.0",
            "components": {
                "process": "alive",
                "models": "available" if runtime is not None else "unavailable",
                "database": database_status,
                "explainability": (
                    "available"
                    if runtime is not None and runtime.explainability is not None
                    else "unavailable"
                ),
                "anomaly_intelligence": (
                    "available"
                    if runtime is not None and runtime.anomaly_experiment is not None
                    else "unavailable"
                ),
            },
        }

    @app.get("/api/v1/ready", tags=["system"], response_model=ReadyResponse)
    def ready(request: Request) -> dict[str, Any]:
        """Readiness reflects verified startup artifacts and the migrated local database."""
        if not getattr(request.app.state, "ready", False):
            raise ApiError(503, "not_ready")
        runtime = getattr(request.app.state, "runtime", None)
        if runtime is None:
            raise ApiError(503, "model_artifacts_unavailable")
        if runtime.explainability is None:
            raise ApiError(503, "explainability_unavailable")
        if runtime.anomaly_experiment is None or runtime.anomaly_reference is None:
            raise ApiError(503, "anomaly_intelligence_unavailable")
        if not getattr(request.app.state, "database_ready", False):
            raise ApiError(503, "database_schema_unavailable")
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
        except SQLAlchemyError as exc:
            raise ApiError(503, "database_unavailable") from exc
        return {
            "status": "ready",
            "model_version": runtime.bundle.metadata["model_version"],
        }

    @app.get("/api/v1/models/current", tags=["models"])
    def current_model(request: Request) -> dict[str, Any]:
        return _runtime(request).current_model

    @app.get("/api/v1/models/capabilities", tags=["models"])
    def capabilities(request: Request) -> dict[str, Any]:
        result = _runtime(request).capabilities
        result["max_batch_rows"] = request.app.state.settings.max_batch_rows
        result["max_explanation_batch"] = request.app.state.settings.max_explanation_batch
        result["max_csv_bytes"] = request.app.state.settings.max_upload_bytes
        result["max_csv_rows"] = request.app.state.settings.max_csv_rows
        result["max_concurrent_analyses"] = request.app.state.settings.max_concurrent_analyses
        return result

    @app.post("/api/v1/predictions", tags=["predictions"], response_model=PredictionResponse)
    def prediction(
        features: FeatureInput,
        request: Request,
        session: SessionDependency,
    ) -> dict[str, Any]:
        result = _decorate_output(
            request,
            _runtime(request).intelligence.intelligence_one(
                _feature_dict(features), include_explanation=False
            ),
        )
        return _persist_single(session, result)

    @app.post(
        "/api/v1/predictions/batch",
        tags=["predictions"],
        response_model=BatchPredictionResponse,
    )
    def prediction_batch(
        body: BatchPredictionRequest,
        request: Request,
        session: SessionDependency,
    ) -> dict[str, Any]:
        _check_batch_limit(request, len(body.transactions))
        if (
            body.include_explanations
            and len(body.transactions) > request.app.state.settings.max_explanation_batch
        ):
            raise ApiError(413, "explanation_batch_limit_exceeded")
        features = pd.DataFrame([_feature_dict(item) for item in body.transactions])
        outputs = [
            _decorate_output(request, output)
            for output in _runtime(request).intelligence.intelligence_batch(
                features,
                include_explanations=body.include_explanations,
                explanation_method=body.explanation_method,
                top_n=body.top_n,
            )
        ]
        records = [save_prediction(session, output) for output in outputs]
        session.commit()
        for output, record in zip(outputs, records, strict=True):
            session.refresh(record)
            output["record_id"] = record.id
            output["timestamp"] = iso_utc(record.created_at)
        return {"count": len(outputs), "results": outputs}

    @app.post("/api/v1/explanations/local", tags=["explanations"])
    def local_explanation(body: LocalExplanationRequest, request: Request) -> dict[str, Any]:
        return _runtime(request).explainability.explain_one(
            _feature_dict(body.features), method=body.method, top_n=body.top_n
        )

    @app.get("/api/v1/explanations/global", tags=["explanations"])
    def global_explanation(request: Request) -> dict[str, Any]:
        runtime = _runtime(request)
        return {
            "model_version": runtime.bundle.metadata["model_version"],
            "output_space": "raw_log_odds",
            "summary_method": "mean absolute and signed validation SHAP values",
            "partition": "validation",
            "features": runtime.global_summary,
            "calibrated_probability_additivity_claim": False,
            "causal_claim": False,
        }

    @app.get("/api/v1/risk/policy", tags=["risk"])
    def risk_policy(request: Request) -> dict[str, Any]:
        policy = _runtime(request).policy.to_dict()
        policy["semantics"] = (
            "operational analyst triage categories; not calibrated probability bands"
        )
        return policy

    @app.post("/api/v1/risk/score", tags=["risk"], response_model=PredictionResponse)
    def risk_score(
        features: FeatureInput,
        request: Request,
        session: SessionDependency,
    ) -> dict[str, Any]:
        result = _decorate_output(
            request,
            _runtime(request).intelligence.intelligence_one(
                _feature_dict(features), include_explanation=False
            ),
        )
        return _persist_single(session, result)

    @app.post("/api/v1/risk/prioritize", tags=["risk"])
    def prioritize(body: PrioritizeRequest, request: Request) -> dict[str, Any]:
        _check_batch_limit(request, len(body.transactions))
        features = pd.DataFrame([_feature_dict(item) for item in body.transactions])
        scored = [
            _decorate_output(request, result)
            for result in _runtime(request).intelligence.intelligence_batch(features)
        ]
        ranking_rows = pd.DataFrame(
            [{**result, "transaction_id": input_index} for input_index, result in enumerate(scored)]
        )
        priority = prioritize_transactions(
            ranking_rows,
            top_k=body.top_k,
            budget_percentage=body.budget_percentage,
            min_probability=body.min_risk_score / 100,
            risk_tiers=set(body.risk_tiers) if body.risk_tiers is not None else None,
            transaction_id_column="transaction_id",
            page_size=len(scored),
        )
        ranked_results = []
        for row in priority.rows.to_dict(orient="records"):
            row["input_index"] = int(row.pop("transaction_id"))
            row.pop("input_position", None)
            ranked_results.append(row)
        return {
            "ranking_semantics": "Mission 03 prioritization: calibrated probability, stable ties",
            "requested_count": len(scored),
            "selected_count": priority.metadata["selected_k"],
            "priority_policy": priority.metadata,
            "results": ranked_results,
        }

    @app.post("/api/v1/anomalies/score", tags=["anomalies"])
    def anomaly_score(body: FeatureBatchRequest, request: Request) -> dict[str, Any]:
        _check_batch_limit(request, len(body.transactions))
        features = pd.DataFrame([_feature_dict(item) for item in body.transactions])
        runtime = _runtime(request)
        scores = anomaly_scores(runtime.anomaly_experiment, features)
        percentiles = anomaly_percentiles(scores, runtime.anomaly_reference)
        categories = anomaly_categories(percentiles)
        return {
            "model_version": runtime.anomaly_experiment.metadata["model_version"],
            "score_direction": "higher = more anomalous",
            "score_is_probability": False,
            "fraud_probability_included": False,
            "results": [
                {
                    "anomaly_score": float(score),
                    "percentile": float(percentile),
                    "category": str(category),
                }
                for score, percentile, category in zip(scores, percentiles, categories, strict=True)
            ],
        }

    @app.post("/api/v1/uploads/csv", tags=["uploads"], response_model=UploadResponse)
    async def upload_csv(
        request: Request,
        file: CSVFileDependency,
        session: SessionDependency,
    ) -> dict[str, Any]:
        settings = request.app.state.settings
        if file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
            await file.close()
            raise ApiError(415, "unsupported_media_type")
        upload_id = str(uuid4())
        storage_name = f"{upload_id}.csv"
        destination = _public_path(settings, storage_name)
        settings.upload_directory.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        try:
            _cleanup_expired_upload_files(settings)
            with destination.open("xb") as output_file:
                while chunk := await file.read(64 * 1024):
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise ApiError(413, "upload_limit_exceeded")
                    digest.update(chunk)
                    output_file.write(chunk)
            row_count = validate_csv_file(destination, max_rows=settings.max_csv_rows)
            upload = Upload(
                id=upload_id,
                storage_name=storage_name,
                sha256=digest.hexdigest(),
                size_bytes=size,
                row_count=row_count,
                created_at=utcnow(),
            )
            session.add(upload)
            session.commit()
        except CSVValidationError as exc:
            session.rollback()
            destination.unlink(missing_ok=True)
            raise ApiError(422, exc.code) from exc
        except ApiError:
            session.rollback()
            destination.unlink(missing_ok=True)
            raise
        except Exception as exc:
            session.rollback()
            destination.unlink(missing_ok=True)
            raise ApiError(500, "upload_failed") from exc
        finally:
            await file.close()
        return {
            "upload_id": upload_id,
            "sha256": digest.hexdigest(),
            "size_bytes": size,
            "row_count": row_count,
            "schema_version": SCHEMA_VERSION,
        }

    @app.post("/api/v1/analyses", tags=["analyses"], response_model=AnalysisResponse)
    def create_analysis(
        body: CreateAnalysisRequest,
        request: Request,
        session: SessionDependency,
    ) -> dict[str, Any]:
        if not request.app.state.analysis_semaphore.acquire(blocking=False):
            raise ApiError(429, "analysis_concurrency_limit")
        job: AnalysisJob | None = None
        try:
            upload = session.get(Upload, body.upload_id)
            if upload is None:
                raise ApiError(404, "upload_not_found")
            if upload.row_count > request.app.state.settings.max_csv_rows:
                raise ApiError(422, "row_limit_exceeded")
            path = _public_path(request.app.state.settings, upload.storage_name)
            if not path.is_file():
                raise ApiError(410, "upload_expired")
            if path.stat().st_size != upload.size_bytes or _sha256(path) != upload.sha256:
                raise ApiError(409, "upload_integrity_mismatch")
            job = AnalysisJob(
                id=new_id(),
                upload_id=upload.id,
                status="pending",
                requested_rows=upload.row_count,
                processed_rows=0,
                created_at=utcnow(),
            )
            session.add(job)
            session.commit()
            job.status = "running"
            job.started_at = utcnow()
            job.model_version = str(_runtime(request).bundle.metadata["model_version"])
            session.commit()

            tier_counts: Counter[str] = Counter()
            anomaly_counts: Counter[str] = Counter()
            probability_total = 0.0
            probability_min = 1.0
            probability_max = 0.0
            flagged_count = 0
            processed = 0
            for first_row, features in iter_csv_batches(
                path,
                chunk_rows=request.app.state.settings.csv_chunk_rows,
                max_rows=request.app.state.settings.max_csv_rows,
            ):
                outputs = [
                    _decorate_output(request, result)
                    for result in _runtime(request).intelligence.intelligence_batch(features)
                ]
                for offset, output in enumerate(outputs):
                    probability = float(output["fraud_probability"])
                    probability_total += probability
                    probability_min = min(probability_min, probability)
                    probability_max = max(probability_max, probability)
                    flagged_count += int(output["predicted_class"] == 1)
                    tier_counts[str(output["risk_tier"])] += 1
                    anomaly = output.get("anomaly") or {}
                    if anomaly:
                        anomaly_counts[str(anomaly["category"])] += 1
                    save_prediction(
                        session,
                        output,
                        source="analysis",
                        analysis_id=job.id,
                        row_number=first_row + offset,
                    )
                processed += len(outputs)
                job.processed_rows = processed
                session.commit()

            if processed != upload.row_count:
                raise ApiError(422, "upload_changed_after_validation")
            job.status = "completed"
            job.processed_rows = processed
            job.completed_at = utcnow()
            job.summary = {
                "rows": processed,
                "flagged_for_review": flagged_count,
                "flagged_percentage": flagged_count / processed * 100,
                "mean_fraud_probability": probability_total / processed,
                "minimum_fraud_probability": probability_min,
                "maximum_fraud_probability": probability_max,
                "risk_tier_counts": dict(tier_counts),
                "anomaly_category_counts": dict(anomaly_counts),
                "created_at": iso_utc(job.created_at),
                "model_version": job.model_version,
                "labels_present": False,
                "precision_recall_computed": False,
            }
            session.commit()
            return analysis_dict(job)
        except ApiError:
            if job is not None:
                session.rollback()
                job = session.get(AnalysisJob, job.id)
                if job is not None:
                    job.status = "failed"
                    job.failure_code = "analysis_failed"
                    job.completed_at = utcnow()
                    session.commit()
            raise
        except Exception as exc:
            session.rollback()
            if job is not None:
                job = session.get(AnalysisJob, job.id)
                if job is not None:
                    job.status = "failed"
                    job.failure_code = "analysis_failed"
                    job.completed_at = utcnow()
                    session.commit()
            logger.error("Analysis failed request_id=%s", _request_id(request))
            raise ApiError(422, "analysis_failed") from exc
        finally:
            request.app.state.analysis_semaphore.release()

    @app.get("/api/v1/analyses", tags=["analyses"])
    def list_analyses(
        session: SessionDependency,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ) -> dict[str, Any]:
        jobs = session.scalars(
            select(AnalysisJob).order_by(AnalysisJob.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return {
            "count": len(jobs),
            "limit": limit,
            "offset": offset,
            "analyses": [analysis_dict(job) for job in jobs],
        }

    @app.get("/api/v1/analyses/{analysis_id}", tags=["analyses"], response_model=AnalysisResponse)
    def get_analysis(analysis_id: str, session: SessionDependency) -> dict[str, Any]:
        return analysis_dict(_missing_analysis(session, analysis_id))

    @app.get("/api/v1/analyses/{analysis_id}/summary", tags=["analyses"])
    def get_analysis_summary(analysis_id: str, session: SessionDependency) -> dict[str, Any]:
        job = _missing_analysis(session, analysis_id)
        return {"analysis_id": job.id, "status": job.status, "summary": job.summary}

    @app.get("/api/v1/analyses/{analysis_id}/results", tags=["analyses"])
    def get_analysis_results(
        analysis_id: str,
        session: SessionDependency,
        limit: int = Query(100, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ) -> dict[str, Any]:
        _missing_analysis(session, analysis_id)
        records = session.scalars(
            select(PredictionRecord)
            .where(PredictionRecord.analysis_id == analysis_id)
            .order_by(PredictionRecord.row_number)
            .limit(limit)
            .offset(offset)
        ).all()
        return {
            "analysis_id": analysis_id,
            "count": len(records),
            "limit": limit,
            "offset": offset,
            "results": [prediction_dict(record) for record in records],
        }

    @app.delete("/api/v1/analyses/{analysis_id}", tags=["analyses"])
    def delete_analysis(
        analysis_id: str,
        request: Request,
        session: SessionDependency,
    ) -> dict[str, Any]:
        job = _missing_analysis(session, analysis_id)
        if job.status in {"pending", "running"}:
            raise ApiError(409, "analysis_in_progress")
        upload = session.get(Upload, job.upload_id)
        storage_name = upload.storage_name if upload else None
        upload_id = upload.id if upload else None
        other_analyses = 0
        if upload is not None:
            other_analyses = (
                session.scalar(
                    select(func.count(AnalysisJob.id)).where(
                        AnalysisJob.upload_id == upload.id,
                        AnalysisJob.id != job.id,
                    )
                )
                or 0
            )
        session.delete(job)
        if upload is not None and other_analyses == 0:
            session.delete(upload)
        session.commit()
        if storage_name and other_analyses == 0:
            try:
                _public_path(request.app.state.settings, storage_name).unlink(missing_ok=True)
            except OSError:
                logger.error("Deleted analysis upload could not be removed")
        elif other_analyses:
            storage_name = None
        return {"analysis_id": analysis_id, "deleted": True, "upload_id": upload_id}

    @app.get("/api/v1/history", tags=["history"])
    def history(
        session: SessionDependency,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        risk_tier: str | None = Query(None, pattern="^(Low|Elevated|High|Critical)$"),
        from_created_at: Annotated[datetime | None, Query(alias="from")] = None,
        to_created_at: Annotated[datetime | None, Query(alias="to")] = None,
        model_version: str | None = Query(None, max_length=160),
        analysis_id: str | None = Query(None, max_length=36),
        sort_order: Literal["asc", "desc"] = Query("desc"),
    ) -> dict[str, Any]:
        filters = []
        if risk_tier is not None:
            filters.append(PredictionRecord.risk_tier == risk_tier)
        if from_created_at is not None:
            start = (
                from_created_at.replace(tzinfo=UTC)
                if from_created_at.tzinfo is None
                else from_created_at
            )
            filters.append(
                PredictionRecord.created_at >= start.astimezone(UTC).replace(tzinfo=None)
            )
        if to_created_at is not None:
            end = (
                to_created_at.replace(tzinfo=UTC) if to_created_at.tzinfo is None else to_created_at
            )
            filters.append(PredictionRecord.created_at <= end.astimezone(UTC).replace(tzinfo=None))
        if from_created_at is not None and to_created_at is not None and start > end:
            raise ApiError(422, "invalid_history_date_range")
        if model_version is not None:
            filters.append(PredictionRecord.model_version == model_version)
        if analysis_id is not None:
            filters.append(PredictionRecord.analysis_id == analysis_id)
        created_order = (
            PredictionRecord.created_at.asc()
            if sort_order == "asc"
            else PredictionRecord.created_at.desc()
        )
        id_order = PredictionRecord.id.asc() if sort_order == "asc" else PredictionRecord.id.desc()
        records = session.scalars(
            select(PredictionRecord)
            .where(*filters)
            .order_by(created_order, id_order)
            .limit(limit)
            .offset(offset)
        ).all()
        total = (
            session.scalar(
                select(func.count()).select_from(
                    select(PredictionRecord.id).where(*filters).subquery()
                )
            )
            or 0
        )
        return {
            "total": total,
            "count": len(records),
            "limit": limit,
            "offset": offset,
            "sort_order": sort_order,
            "stable_sort": "created_at plus record_id",
            "results": [prediction_dict(record) for record in records],
        }

    @app.get("/api/v1/history/{record_id}", tags=["history"])
    def history_item(record_id: str, session: SessionDependency) -> dict[str, Any]:
        record = session.get(PredictionRecord, record_id)
        if record is None:
            raise ApiError(404, "record_not_found")
        return prediction_dict(record)

    @app.post("/api/v1/investigations", tags=["investigations"])
    def create_investigation(
        body: InvestigationCreate,
        session: SessionDependency,
    ) -> dict[str, Any]:
        if (
            body.prediction_id is not None
            and session.get(PredictionRecord, body.prediction_id) is None
        ):
            raise ApiError(404, "prediction_not_found")
        item = Investigation(
            id=new_id(),
            prediction_id=body.prediction_id,
            title=body.title.strip(),
            reason=body.reason.strip(),
            status="Open",
            outcome=None,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(item)
        add_investigation_event(session, item.id, "created", None, "Open")
        session.commit()
        return investigation_dict(item)

    @app.get("/api/v1/investigations", tags=["investigations"])
    def list_investigations(
        session: SessionDependency,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        status: str | None = Query(None, pattern="^(Open|In Review|Escalated|Closed)$"),
    ) -> dict[str, Any]:
        query = select(Investigation)
        if status is not None:
            query = query.where(Investigation.status == status)
        items = session.scalars(
            query.order_by(Investigation.updated_at.desc()).limit(limit).offset(offset)
        ).all()
        return {
            "count": len(items),
            "limit": limit,
            "offset": offset,
            "investigations": [investigation_dict(item) for item in items],
        }

    @app.get("/api/v1/investigations/{investigation_id}", tags=["investigations"])
    def get_investigation(investigation_id: str, session: SessionDependency) -> dict[str, Any]:
        return investigation_dict(
            _missing_investigation(session, investigation_id), include_notes=True
        )

    @app.patch("/api/v1/investigations/{investigation_id}", tags=["investigations"])
    def update_investigation(
        investigation_id: str,
        body: InvestigationPatch,
        session: SessionDependency,
    ) -> dict[str, Any]:
        if not body.model_fields_set:
            raise ApiError(422, "empty_investigation_update")
        if body.status is None and body.outcome is None:
            raise ApiError(422, "empty_investigation_update")
        item = _missing_investigation(session, investigation_id)
        if body.status is not None and body.status != item.status:
            if body.status not in _STATUS_TRANSITIONS[item.status]:
                raise ApiError(409, "invalid_status_transition")
            old_status = item.status
            item.status = body.status
            add_investigation_event(session, item.id, "status_changed", old_status, item.status)
        if body.outcome is not None and body.outcome != item.outcome:
            old_outcome = item.outcome
            item.outcome = body.outcome
            add_investigation_event(session, item.id, "outcome_recorded", old_outcome, item.outcome)
        item.updated_at = utcnow()
        session.commit()
        return investigation_dict(item)

    @app.post("/api/v1/investigations/{investigation_id}/notes", tags=["investigations"])
    def add_note(
        investigation_id: str,
        body: NoteCreate,
        session: SessionDependency,
    ) -> dict[str, Any]:
        item = _missing_investigation(session, investigation_id)
        note = new_note(session, item.id, body.body)
        item.updated_at = utcnow()
        add_investigation_event(session, item.id, "note_added", None, None)
        session.commit()
        return {
            "note_id": note.id,
            "investigation_id": item.id,
            "created_at": note.created_at.isoformat(),
        }

    return app


app = create_app()
