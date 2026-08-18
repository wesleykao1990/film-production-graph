"""M04a candidate-selection application boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from film_graph.domain import ActorRef, ArtifactVersion, LifecycleStatus

from .errors import NotFoundError, ValidationError
from .ports import GraphRepository
from .service import FilmGraphApplicationService


@dataclass(frozen=True, slots=True)
class SelectPremiseCandidateCommand:
    """Select one human-approved premise branch without deleting alternatives."""

    project_id: UUID
    candidate_version_ids: tuple[UUID, ...]
    selected_version_id: UUID
    expected_current_revision: int
    actor: ActorRef
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_version_ids", tuple(self.candidate_version_ids))


class StoryRoomApplicationService:
    """Thin M04a use cases composed over the existing graph service."""

    def __init__(self, graph_service: FilmGraphApplicationService | GraphRepository) -> None:
        if isinstance(graph_service, FilmGraphApplicationService):
            self.graph_service = graph_service
        else:
            self.graph_service = FilmGraphApplicationService(graph_service)

    @property
    def repository(self) -> GraphRepository:
        return self.graph_service.repository

    def select_premise_candidate(self, command: SelectPremiseCandidateCommand) -> ArtifactVersion:
        """Approve only the selected, current premise version.

        Validation completes for every candidate before the existing lifecycle
        command is called.  Rejected branches are intentionally left untouched.
        """

        command.actor.require_human()
        if not command.rationale.strip():
            raise ValidationError("selection rationale must not be empty")
        if len(command.candidate_version_ids) < 2:
            raise ValidationError("at least two premise candidates are required")
        if len(set(command.candidate_version_ids)) != len(command.candidate_version_ids):
            raise ValidationError("premise candidate version IDs must be distinct")
        if command.selected_version_id not in command.candidate_version_ids:
            raise ValidationError("selected premise candidate must be in the candidate set")
        if command.expected_current_revision < 1:
            raise ValidationError("expected_current_revision must be >= 1")
        if self.repository.get_project(command.project_id) is None:
            raise NotFoundError(f"project not found: {command.project_id}")

        for version_id in command.candidate_version_ids:
            version = self.repository.get_version(version_id)
            if version is None:
                raise NotFoundError(f"premise candidate version not found: {version_id}")
            identity = self.repository.get_identity(version.artifact_id)
            if identity is None:
                raise NotFoundError(f"artifact not found: {version.artifact_id}")
            if (
                version.project_id != command.project_id
                or identity.project_id != command.project_id
            ):
                raise ValidationError("all premise candidates must belong to the requested project")
            if identity.artifact_type != "premise_candidate":
                raise ValidationError("all selected branches must be premise_candidate artifacts")

        return self.graph_service.transition_version(
            # Lifecycle transition is the sole mutation and records the human
            # rationale through the existing approval/human-decision path.
            command=_transition_command(command)
        )


def _transition_command(command: SelectPremiseCandidateCommand) -> Any:
    # Local import avoids changing the application port surface for this
    # milestone-specific command.
    from .commands import TransitionVersionCommand

    return TransitionVersionCommand(
        version_id=command.selected_version_id,
        target_status=LifecycleStatus.APPROVED,
        actor=command.actor,
        expected_current_revision=command.expected_current_revision,
        rationale=command.rationale.strip(),
    )


__all__ = ["SelectPremiseCandidateCommand", "StoryRoomApplicationService"]
