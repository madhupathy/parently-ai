"""Database helpers for the Parently backend."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings
from .models import Base


class Database:
    """Thin wrapper around SQLAlchemy engine/session handling."""

    def __init__(self) -> None:
        settings = get_settings()
        engine_kwargs: dict = {"future": True}
        if settings.is_postgres:
            engine_kwargs.update(
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
        self.engine = create_engine(settings.backend_database_url, **engine_kwargs)
        self._session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def get_db() -> Database:
    """Return a shared Database instance."""

    return _DB


_DB = Database()
