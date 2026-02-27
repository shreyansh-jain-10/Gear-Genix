"""
Database engine and session management.

This module centralises SQLAlchemy setup so that all other parts of the
application share the same engine and session factory.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

import config


# Create the SQLAlchemy engine using the configured PostgreSQL URL.
engine = create_engine(config.DATABASE_URL, echo=False, future=True)

# Base class for all ORM models.
Base = declarative_base()

# Session factory for creating database sessions.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Context manager that yields a SQLAlchemy Session.

    Ensures that sessions are always properly closed and that callers
    have a clear place to manage transactions.
    """

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
