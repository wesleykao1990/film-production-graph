"""Domain errors shared by application and persistence adapters."""


class DomainError(ValueError):
    """Base class for invalid domain values or commands."""


class InvalidLifecycleTransition(DomainError):
    """Raised when a version cannot move to the requested lifecycle state."""


class InvalidActor(DomainError):
    """Raised when an actor reference is malformed or lacks authority."""


class AuthorityError(DomainError):
    """Raised when an agent/system actor attempts a human-only command."""


class InvalidRights(DomainError):
    """Raised when a rights block is incomplete or internally inconsistent."""


class RightsRequired(DomainError):
    """Raised when an asset approval has no usable rights record."""
