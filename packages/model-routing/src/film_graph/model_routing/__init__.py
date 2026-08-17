"""Application-owned model alias routing with no gateway or SDK dependency."""

from .aliases import ModelAlias, ModelAliasRegistry, ResolvedModel, resolve_model_alias
from .errors import InvalidModelAlias, ModelRoutingError, UnknownModelAlias

__all__ = [
    "InvalidModelAlias",
    "ModelAlias",
    "ModelAliasRegistry",
    "ModelRoutingError",
    "ResolvedModel",
    "UnknownModelAlias",
    "resolve_model_alias",
]
