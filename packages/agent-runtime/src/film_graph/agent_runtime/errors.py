"""Agent-runtime boundary errors."""


class AgentRuntimeError(RuntimeError):
    """Base class for deterministic runtime failures."""


class NetworkAccessDenied(AgentRuntimeError):
    """Raised by the optional test guard when code attempts network egress."""


class PermissionDenied(AgentRuntimeError):
    """A tool or artifact capability is outside the effective intersection."""


class ProjectScopeViolation(AgentRuntimeError):
    """A tool attempted to access data outside the run project."""


class BudgetExceeded(AgentRuntimeError):
    """A model request would exceed the immutable run budget."""


class OutputContractError(AgentRuntimeError):
    """Model output does not match the role's declared proposal contract."""


class UnknownAgent(AgentRuntimeError):
    """The requested agent role is not registered."""


class RuntimeExecutionError(AgentRuntimeError):
    """A bounded offline model run failed without producing a proposal."""
