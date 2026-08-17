"""Agent-runtime boundary errors."""


class AgentRuntimeError(RuntimeError):
    """Base class for deterministic runtime failures."""


class NetworkAccessDenied(AgentRuntimeError):
    """Raised by the optional test guard when code attempts network egress."""
