"""Persistence-specific availability and translation errors."""

from film_graph.application.errors import ApplicationError


class PersistenceError(ApplicationError):
    """Base class for database adapter failures."""


class PersistenceUnavailable(PersistenceError):
    """Psycopg or the configured database is unavailable."""
