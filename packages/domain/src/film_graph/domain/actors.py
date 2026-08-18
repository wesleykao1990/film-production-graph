"""Actor and authority value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .errors import AuthorityError, InvalidActor


class ActorType(StrEnum):
    USER = "user"
    AGENT = "agent"
    WORKFLOW = "workflow"
    SYSTEM = "system"
    IMPORT = "import"


@dataclass(frozen=True, slots=True)
class ActorRef:
    actor_type: ActorType
    actor_id: str
    display_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor_type", ActorType(self.actor_type))
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise InvalidActor("actor_id must be a non-empty string")
        object.__setattr__(self, "actor_id", self.actor_id.strip())

    @property
    def is_human(self) -> bool:
        return self.actor_type is ActorType.USER

    def require_human(self) -> None:
        if not self.is_human:
            raise AuthorityError("this command requires a human user actor")

    def require_validator(self) -> None:
        if self.actor_type not in {ActorType.USER, ActorType.SYSTEM, ActorType.WORKFLOW}:
            raise AuthorityError("this command requires a user, workflow, or system validator")

    def as_dict(self) -> dict[str, str]:
        result = {"actor_type": self.actor_type.value, "actor_id": self.actor_id}
        if self.display_name is not None:
            result["display_name"] = self.display_name
        return result
