"""Database engine and session configuration."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_DATABASE_URL = "sqlite:///data/zunder-zapfe.db"


def database_url(default: str | None = None) -> str:
    return os.environ.get("ZUNDER_ZAPFE_DATABASE_URL", default or DEFAULT_DATABASE_URL)


def create_database_engine(url: str | None = None) -> Engine:
    """Create an engine with SQLite integrity and concurrency safeguards."""
    resolved_url = url or database_url()
    parsed_url = make_url(resolved_url)
    engine_options: dict[str, object] = {}

    if parsed_url.get_backend_name() == "sqlite":
        engine_options["connect_args"] = {"check_same_thread": False}
        if parsed_url.database in {None, "", ":memory:"}:
            engine_options["poolclass"] = StaticPool
        elif parsed_url.database:
            Path(parsed_url.database).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )

    engine = create_engine(resolved_url, **engine_options)
    if parsed_url.get_backend_name() == "sqlite":
        _configure_sqlite(engine)
    return engine


def _configure_sqlite(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(
        dbapi_connection: sqlite3.Connection, _connection_record: object
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.close()


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
