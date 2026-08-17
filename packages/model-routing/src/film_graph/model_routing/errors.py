"""Errors for application-owned model alias routing."""


class ModelRoutingError(ValueError):
    """Base class for invalid alias configuration or lookup."""


class UnknownModelAlias(ModelRoutingError):
    """Raised when a call requests an alias absent from application config."""


class InvalidModelAlias(ModelRoutingError):
    """Raised when an alias entry is incomplete or malformed."""
