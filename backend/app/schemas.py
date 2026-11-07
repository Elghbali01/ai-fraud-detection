"""Strict request and response models for the versioned local API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    create_model,
    field_validator,
    model_validator,
)

from fraud_detection.schema import FEATURE_COLUMNS


class FeatureInputBase(BaseModel):
    """Reject string coercion, booleans, target labels, and extra feature names."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @field_validator("*", mode="before")
    @classmethod
    def require_json_number(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("feature values must be JSON numbers")
        return value


class ApiErrorResponse(BaseModel):
    """Stable sanitized response for transport and request validation failures."""

    error: str
    message: str
    request_id: str
    timestamp: datetime
    details: list[dict[str, str]] | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    api_version: str
    components: dict[str, str]


class ReadyResponse(BaseModel):
    status: str
    model_version: str


class PredictionResponse(BaseModel):
    contract_version: str
    record_id: str
    model_version: str
    schema_version: str
    transaction_id: str | int | None
    fraud_probability: float
    risk_score: float
    risk_tier: str
    predicted_class: int
    decision_threshold: float
    decision_status: str
    probability_calibration_status: str
    risk_policy_version: str
    anomaly: dict | None
    explanation: dict | None
    narrative: list[str]
    timestamp: datetime


class BatchPredictionResponse(BaseModel):
    count: int
    results: list[PredictionResponse]


class AnalysisResponse(BaseModel):
    analysis_id: str
    upload_id: str
    status: Literal["pending", "running", "completed", "failed"]
    requested_rows: int
    processed_rows: int
    model_version: str | None
    failure_code: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    summary: dict | None


FeatureInput = create_model(
    "FeatureInput",
    __base__=FeatureInputBase,
    **{column: (FiniteFloat, ...) for column in FEATURE_COLUMNS},
)


class BatchPredictionRequest(BaseModel):
    """Bounded feature batch for prediction and prioritization."""

    model_config = ConfigDict(extra="forbid")
    transactions: list[FeatureInput] = Field(min_length=1, max_length=1_000)
    include_explanations: bool = False
    explanation_method: Literal["linear_log_odds", "shap_interventional_log_odds"] = (
        "linear_log_odds"
    )
    top_n: int | None = Field(default=10, ge=1, le=30)


class FeatureBatchRequest(BaseModel):
    """Bounded feature-only batch for endpoints that do not accept explanation options."""

    model_config = ConfigDict(extra="forbid")
    transactions: list[FeatureInput] = Field(min_length=1, max_length=1_000)


class LocalExplanationRequest(BaseModel):
    """One exact-schema feature vector and an explicitly named attribution method."""

    model_config = ConfigDict(extra="forbid")
    features: FeatureInput
    method: Literal["linear_log_odds", "shap_interventional_log_odds"] = "linear_log_odds"
    top_n: int | None = Field(default=10, ge=1, le=30)


class PrioritizeRequest(BaseModel):
    """Bounded batch and one explicit alert budget for descending-risk triage."""

    model_config = ConfigDict(extra="forbid")
    transactions: list[FeatureInput] = Field(min_length=1, max_length=1_000)
    top_k: int | None = Field(default=None, ge=1, le=1_000)
    budget_percentage: FiniteFloat | None = Field(default=None, gt=0, le=100)
    min_risk_score: FiniteFloat = Field(default=0, ge=0, le=100)
    risk_tiers: list[Literal["Low", "Elevated", "High", "Critical"]] | None = None

    @model_validator(mode="after")
    def require_one_budget(self) -> PrioritizeRequest:
        if (self.top_k is None) == (self.budget_percentage is None):
            raise ValueError("specify exactly one of top_k or budget_percentage")
        if self.risk_tiers is not None and len(set(self.risk_tiers)) != len(self.risk_tiers):
            raise ValueError("risk_tiers must not contain duplicates")
        return self


class UploadResponse(BaseModel):
    """Public metadata for a validated CSV upload."""

    upload_id: str
    sha256: str
    size_bytes: int
    row_count: int
    schema_version: str


class CreateAnalysisRequest(BaseModel):
    """Reference a validated upload by its server-generated UUID."""

    model_config = ConfigDict(extra="forbid")
    upload_id: str


class InvestigationCreate(BaseModel):
    """Create a manual analyst investigation."""

    model_config = ConfigDict(extra="forbid")
    prediction_id: str | None = None
    title: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=1_000)


class InvestigationPatch(BaseModel):
    """Update the workflow state or manually recorded outcome."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["Open", "In Review", "Escalated", "Closed"] | None = None
    outcome: Literal["Unconfirmed", "Legitimate", "Confirmed Fraud", "Inconclusive"] | None = None


class NoteCreate(BaseModel):
    """Add one bounded analyst note."""

    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=4_000)


PageSize = Annotated[int, Field(ge=1, le=100)]
