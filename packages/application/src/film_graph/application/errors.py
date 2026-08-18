"""Application command/query failures mapped by the API layer."""


class ApplicationError(RuntimeError):
    """Base class for application boundary failures."""


class NotFoundError(ApplicationError):
    """Requested project/entity/version does not exist."""


class ConflictError(ApplicationError):
    """Optimistic concurrency or graph constraint conflict."""


class ValidationError(ApplicationError, ValueError):
    """Command input failed an application/domain rule."""
