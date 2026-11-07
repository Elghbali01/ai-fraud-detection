"""SQLite engine construction with foreign-key enforcement."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create a local SQLite engine and enable foreign-key checks per connection."""
    if not database_url.startswith("sqlite:"):
        raise ValueError("Mission 04 supports local SQLite only")
    path_text = database_url.removeprefix("sqlite:///")
    Path(path_text).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False, "timeout": 15},
        echo=echo,
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return an explicit SQLAlchemy 2.x session factory."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
