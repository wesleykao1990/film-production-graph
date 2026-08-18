"""Lazy Psycopg 3 connection helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .errors import PersistenceUnavailable


def connect(dsn: str | None = None) -> Any:
    """Open a Psycopg 3 connection without importing a provider/client SDK."""

    database_url = dsn or os.getenv("FPG_DATABASE_URL")
    if not database_url:
        raise PersistenceUnavailable("FPG_DATABASE_URL is not configured")
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise PersistenceUnavailable(
            "psycopg[binary] is required for Postgres persistence"
        ) from exc
    try:
        return psycopg.connect(database_url, row_factory=dict_row)
    except Exception as exc:  # psycopg exposes several operational subclasses
        raise PersistenceUnavailable("could not connect to configured Postgres") from exc


@contextmanager
def connection_scope(connection: Any | None = None, dsn: str | None = None) -> Iterator[Any]:
    """Yield a connection and close only connections opened by this scope."""

    owned = connection is None
    current = connection or connect(dsn)
    try:
        yield current
    finally:
        if owned:
            current.close()
