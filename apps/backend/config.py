"""Configuration utilities for the Parently backend."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


load_dotenv()

def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass()
class Settings:
    """Simple configuration container backed by environment variables."""

    backend_database_url: str = field(
        default_factory=lambda: os.getenv("BACKEND_DATABASE_URL", "sqlite:///./parently.db")
    )
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "./data")))
    pdf_folder: Path = field(default_factory=lambda: Path(os.getenv("PDF_FOLDER", "./uploads")))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    gmail_client_secrets_path: Path = field(
        default_factory=lambda: Path(os.getenv("GMAIL_CLIENT_SECRETS_PATH", "./client_secrets.json"))
    )
    gmail_token_path: Path = field(default_factory=lambda: Path(os.getenv("GMAIL_TOKEN_PATH", "./token.json")))
    gmail_query: str = field(default_factory=lambda: os.getenv("GMAIL_QUERY", "in:inbox newer_than:7d"))
    rag_chunk_size: int = field(default_factory=lambda: _get_int("RAG_CHUNK_SIZE", 1000))
    rag_chunk_overlap: int = field(default_factory=lambda: _get_int("RAG_CHUNK_OVERLAP", 200))
    rag_top_k: int = field(default_factory=lambda: _get_int("RAG_TOP_K", 5))

    # Gemini
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))

    # Stripe
    stripe_secret_key: Optional[str] = field(default_factory=lambda: os.getenv("STRIPE_SECRET_KEY"))
    stripe_webhook_secret: Optional[str] = field(default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET"))
    stripe_price_id: Optional[str] = field(default_factory=lambda: os.getenv("STRIPE_PRICE_ID"))
    frontend_app_url: str = field(default_factory=lambda: os.getenv("FRONTEND_APP_URL", "http://localhost:3000"))

    # JWT / Auth
    nextauth_secret: str = field(default_factory=lambda: os.getenv("NEXTAUTH_SECRET", "dev-nextauth-secret"))

    # CORS
    allowed_origins: str = field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*"))

    # Cron
    cron_secret: Optional[str] = field(default_factory=lambda: os.getenv("CRON_SECRET"))

    # SMTP / Support email
    smtp_host: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: _get_int("SMTP_PORT", 587))
    smtp_user: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_USER"))
    smtp_password: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    smtp_from: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_FROM"))
    smtp_from_name: str = field(default_factory=lambda: os.getenv("SMTP_FROM_NAME", "Parently Support"))
    smtp_secure: bool = field(default_factory=lambda: _get_bool("SMTP_SECURE", False))
    support_email: str = field(default_factory=lambda: os.getenv("SUPPORT_EMAIL", "support@parently-ai.com"))

    def __post_init__(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_folder.mkdir(parents=True, exist_ok=True)

    @property
    def is_postgres(self) -> bool:
        return self.backend_database_url.startswith("postgresql")

    @property
    def cors_origins(self) -> list:
        if self.allowed_origins == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()
