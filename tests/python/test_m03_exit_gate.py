from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from film_graph.agent_runtime import (
    ArtifactSnapshot,
    FilmRunContext,
    PermissionSet,
    RunBudget,
    SkillRef,
    TypedAgentRuntime,
)
from film_graph.application import (
    BindProjectSkillCommand,
    CreateArtifactCommand,
    CreateProjectCommand,
    CreateRunCommand,
    FilmGraphApplicationService,
    InMemoryGraphRepository,
    TransitionVersionCommand,
)
from film_graph.domain import ActorRef, ActorType, LifecycleStatus
from film_graph.model_routing import ModelAliasRegistry
from film_graph.skills import SkillRegistry
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

ROOT = Path(__file__).resolve().parents[2]


def test_approved_scene_contract_becomes_typed_locked_skill_proposal() -> None:
    repository = InMemoryGraphRepository()
    service = FilmGraphApplicationService(repository)
    human = ActorRef(ActorType.USER, "director-1")
    agent_actor = ActorRef(ActorType.AGENT, "dialogue-agent-1")
    project = service.create_project(CreateProjectCommand("M03 exit film"))
    scene = service.create_artifact(
        CreateArtifactCommand(
            project.id,
            "scene_contract",
            "scene-S07",
            {
                "objective": "Mara must recover the key",
                "opposition": "Ivo refuses to admit he has it",
                "turn": "Mara recognizes the ink stain",
                "state_delta": "Mara obtains the key",
                "knowledge_delta": "Ivo learns Mara saw the ledger",
            },
            human,
        )
    )
    for status in (
        LifecycleStatus.VALIDATED,
        LifecycleStatus.HUMAN_REVIEW,
        LifecycleStatus.APPROVED,
    ):
        scene = service.transition_version(
            TransitionVersionCommand(scene.id, status, human, 1)
        )

    skill_registry = SkillRegistry(
        repository_root=ROOT,
        skill_roots=[Path("skills")],
        lock_path=Path("skills.lock"),
    )
    snapshot = skill_registry.reload()
    skill = snapshot.get("subtext-pass")
    ref = skill.locked_ref
    service.bind_project_skill(
        BindProjectSkillCommand(
            project_id=project.id,
            agent_ref=agent_actor.actor_id,
            skill_name=ref.name,
            source_path=ref.source_path,
            source_commit=ref.source_commit,
            content_hash=ref.content_hash,
            metadata_version=ref.metadata_version,
            snapshot_hash=snapshot.snapshot_hash,
            actor=human,
        )
    )
    aliases = ModelAliasRegistry.from_json_file(
        ROOT / "machine-readable/model-aliases.example.json"
    )
    manifest = skill.manifest
    tools = frozenset(str(item) for item in manifest["permissions"]["tools"])
    read_types = frozenset(
        str(item) for item in manifest["permissions"]["artifacts"]["read"]
    )
    propose_types = frozenset(
        str(item) for item in manifest["permissions"]["artifacts"]["propose"]
    )
    skill_permissions = PermissionSet(tools, read_types, propose_types)
    application_permissions = PermissionSet(
        tools
        | frozenset(
            {
                "query_edges",
                "retrieve_evidence",
                "propose_artifact",
                "report_finding",
            }
        ),
        read_types,
        propose_types,
    )
    run_id = uuid4()
    context = FilmRunContext(
        project_id=project.id,
        run_id=run_id,
        skill_snapshot_hash=snapshot.snapshot_hash,
        resolved_model=aliases.resolve("story_test"),
        budget=RunBudget(
            max_model_calls=int(manifest["budgets"]["max_model_calls"]),
            max_cost_usd=Decimal(str(manifest["budgets"]["max_cost_usd"])),
            estimated_call_cost_usd=Decimal("0.01"),
        ),
        application_permissions=application_permissions,
        skill_permissions=skill_permissions,
        project_permissions=application_permissions,
        artifacts=(
            ArtifactSnapshot(
                scene.project_id,
                scene.artifact_id,
                scene.id,
                "scene_contract",
                scene.content_hash,
                scene.payload,
                scene.lifecycle_status.value,
            ),
        ),
        skill_refs=(
            SkillRef(
                ref.name,
                ref.source_path,
                ref.source_commit,
                ref.content_hash,
                ref.metadata_version,
                snapshot.snapshot_hash,
            ),
        ),
        skill_instructions={skill.name: skill.instructions},
        skill_resources={skill.name: skill_registry.read_all_resources(skill.name)},
    )

    def screenplay_response(_messages: object, info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            [
                ToolCallPart(
                    info.output_tools[0].name,
                    {
                        "target_version_id": str(scene.id),
                        "replacement_text": (
                            "INT. ARCHIVE — NIGHT\n"
                            "Mara studies the blue ink on Ivo's thumb.\n"
                            "MARA\nYou always did prefer fountain pens."
                        ),
                        "invariants": ["same_scene_outcome", "same_character_knowledge"],
                    },
                )
            ]
        )

    result = TypedAgentRuntime().run(
        "dialogue_patch",
        context,
        "Reduce direct exposition while preserving the approved contract.",
        model=FunctionModel(
            screenplay_response, model_name=context.resolved_model.model
        ),
    )
    provenance = result.provenance_dict()
    patch = service.create_artifact(
        CreateArtifactCommand(
            project.id,
            "screenplay_patch",
            "scene-S07-subtext-pass",
            result.output.model_dump(mode="json"),
            agent_actor,
            provenance=provenance,
        )
    )
    run = service.create_run(
        CreateRunCommand(
            project_id=project.id,
            actor=agent_actor,
            provenance=provenance,
            model_alias=context.resolved_model.alias,
            resolved_provider=context.resolved_model.provider,
            resolved_model=context.resolved_model.model,
            disposition="proposed",
            run_id=run_id,
        )
    )

    assert patch.lifecycle_status is LifecycleStatus.DRAFT
    assert patch.created_by.actor_type is ActorType.AGENT
    assert run.id == run_id
    assert run.provenance["skills"][0]["content_hash"] == ref.content_hash
    assert run.provenance["input_versions"][0]["content_hash"] == scene.content_hash
    assert run.provenance["disposition"] == "proposed"
    assert run.resolved_provider == "fake"
