"""Tests for config.py Settings."""

from __future__ import annotations

import os
from unittest.mock import patch


class TestSettings:
    """Tests for Settings dataclass and properties."""

    def test_is_postgres_with_postgres_url(self) -> None:
        with patch.dict(os.environ, {"BACKEND_DATABASE_URL": "postgresql://user:pass@host/db"}):
            from config import Settings
            s = Settings()
            assert s.is_postgres is True

    def test_is_postgres_with_sqlite_url(self) -> None:
        with patch.dict(os.environ, {"BACKEND_DATABASE_URL": "sqlite:///./test.db"}):
            from config import Settings
            s = Settings()
            assert s.is_postgres is False

    def test_cors_origins_wildcard(self) -> None:
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "*"}):
            from config import Settings
            s = Settings()
            assert s.cors_origins == ["*"]

    def test_cors_origins_csv(self) -> None:
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "http://localhost:3000, https://parently.app"}):
            from config import Settings
            s = Settings()
            assert s.cors_origins == ["http://localhost:3000", "https://parently.app"]

    def test_default_nextauth_secret(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            env = os.environ.copy()
            env.pop("NEXTAUTH_SECRET", None)
            with patch.dict(os.environ, env, clear=True):
                from config import Settings
                s = Settings()
                assert s.nextauth_secret == "dev-nextauth-secret"

    def test_gemini_defaults(self) -> None:
        from config import Settings
        s = Settings()
        assert s.gemini_model == "gemini-1.5-flash"
