"""Versioned plain-Python response contracts for future services."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

CONTRACT_VERSION = "mission03-intelligence-v1"


@dataclass(frozen=True)
class IntelligenceRecord:
    """One transaction's separated supervised, tier, anomaly, and explanation outputs."""

    contract_version: str
    model_version: str
    schema_version: str
    transaction_id: str | int | None
    fraud_probability: float
    risk_score: float
    risk_tier: str
    predicted_class: int
    decision_threshold: float
    decision_status: str
    anomaly: dict[str, Any] | None = None
    explanation: dict[str, Any] | None = None
    narrative: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        result = asdict(self)
        result["narrative"] = list(self.narrative)
        return result
