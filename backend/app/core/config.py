"""Validated local-only API configuration."""

from __future__ import annotations

import ipaddress
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Resource limits and paths for one local API process."""

    model_config = SettingsConfigDict(
        env_prefix="FRAUD_API_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Fraud Detection & Explainable Intelligence API"
    app_env: Literal["development", "test"] = "development"
    enable_docs: bool = True
    project_root: Path = PROJECT_ROOT
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    )
    database_path: Path = PROJECT_ROOT / "data" / "backend" / "mission04.sqlite3"
    upload_directory: Path = PROJECT_ROOT / "data" / "uploads"
    max_json_body_bytes: int = 2 * 1024 * 1024
    max_upload_bytes: int = 32 * 1024 * 1024
    max_csv_rows: int = 20_000
    csv_chunk_rows: int = 256
    max_batch_rows: int = 1_000
    max_explanation_batch: int = 25
    max_concurrent_analyses: int = 1
    max_page_size: int = 100
    upload_retention_hours: int = 24

    @field_validator("host")
    @classmethod
    def require_loopback(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized == "localhost":
            return normalized
        try:
            address = ipaddress.ip_address(normalized)
        except ValueError as exc:
            raise ValueError("API host must be localhost or a loopback IP address") from exc
        if not address.is_loopback:
            raise ValueError("API host must be a loopback IP address")
        return normalized

    @field_validator("cors_origins")
    @classmethod
    def require_explicit_local_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if "*" in values:
            raise ValueError("Wildcard CORS origins are not allowed")
        allowed_hosts = {"localhost", "127.0.0.1", "[::1]", "::1"}
        for origin in values:
            if not origin.startswith(("http://", "https://")):
                raise ValueError("CORS origins must be explicit HTTP(S) origins")
            host = urlsplit(origin).hostname
            if host not in allowed_hosts:
                raise ValueError("CORS origins must use a local host")
        return values

    @model_validator(mode="after")
    def check_limits(self) -> Settings:
        positive = (
            self.port,
            self.max_json_body_bytes,
            self.max_upload_bytes,
            self.max_csv_rows,
            self.csv_chunk_rows,
            self.max_batch_rows,
            self.max_explanation_batch,
            self.max_concurrent_analyses,
            self.max_page_size,
            self.upload_retention_hours,
        )
        if any(value < 1 for value in positive):
            raise ValueError("API limits and port must be positive")
        if self.port > 65_535:
            raise ValueError("API port must be in the TCP/UDP port range")
        if self.max_upload_bytes > 128 * 1024 * 1024:
            raise ValueError("Configured upload limit may not exceed 128 MiB")
        if self.max_batch_rows > 10_000:
            raise ValueError("Configured batch limit may not exceed 10,000 rows")
        if self.max_explanation_batch > self.max_batch_rows:
            raise ValueError("Explanation batch limit may not exceed batch limit")
        return self

    @property
    def database_url(self) -> str:
        """Return an absolute SQLite URL for SQLAlchemy and Alembic."""
        path = (
            self.database_path
            if self.database_path.is_absolute()
            else self.project_root / self.database_path
        )
        return f"sqlite:///{path.resolve().as_posix()}"
