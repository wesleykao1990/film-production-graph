"""Provider-neutral errors."""


class ProviderContractError(RuntimeError):
    """Base class for failures at a provider port."""


class ProviderUnavailable(ProviderContractError):
    """The selected provider is not configured or available."""


class ProviderRequestRejected(ProviderContractError):
    """A provider port rejected an invalid request."""
