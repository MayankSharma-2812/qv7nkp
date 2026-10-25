"""
app/db/session.py

Database configuration and session management for SQLAlchemy 2.x and SQLite.
"""

import os
from pathlib import Path
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base

DEFAULT_DB_FILE = "data/gridbricks.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_FILE}"


def get_default_db_url() -> str:
    """
    Resolve SQLite database URL in order of preference:
    1. DATABASE_URL environment variable.
    2. GRIDBRICKS_DB_PATH environment variable.
    3. Packaged historical snapshot in 'data/gridbricks.db' (relative to backend).
    4. Packaged historical snapshot in 'backend/data/gridbricks.db' (relative to root).
    5. Local working directory 'gridbricks.db'.
    6. Parent directory '../gridbricks.db'.
    7. Fallback 'sqlite:///data/gridbricks.db'.
    """
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]
    if "GRIDBRICKS_DB_PATH" in os.environ:
        return f"sqlite:///{os.environ['GRIDBRICKS_DB_PATH']}"

    candidates = [
        Path("data/gridbricks.db"),
        Path("backend/data/gridbricks.db"),
        Path("gridbricks.db"),
        Path("../gridbricks.db"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return f"sqlite:///{candidate.resolve()}"

    return "sqlite:///data/gridbricks.db"


def get_engine(db_url: str | None = None, echo: bool = False) -> Engine:
    """
    Create a SQLAlchemy Engine for SQLite with connection pool settings
    optimized for single-file embedded workloads.
    """
    url = db_url or get_default_db_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        url,
        echo=echo,
        connect_args=connect_args,
        future=True,
    )


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a sessionmaker bound to the given engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """Create all database tables if they do not exist."""
    Base.metadata.create_all(engine)
