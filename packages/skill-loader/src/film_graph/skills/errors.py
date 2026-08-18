"""Errors raised by the reviewed repository-skill boundary."""


class SkillError(ValueError):
    """Base class for invalid skill packages, locks, and snapshots."""


class SkillSecurityError(SkillError):
    """Raised when a package violates a path, content, or permission boundary."""


class SkillValidationError(SkillError):
    """Raised when portable metadata, manifests, schemas, or tests are invalid."""


class SkillLockError(SkillError):
    """Raised when discovered package content does not match ``skills.lock``."""


class SkillNotFoundError(SkillError):
    """Raised when a resolved snapshot does not contain a requested skill."""
