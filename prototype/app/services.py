from __future__ import annotations

from typing import Any

from .agent import AgentError, MockAgentProvider
from .repository import Repository, RepositoryError
from .skills import SkillError, SkillRegistry
from .workflows import WorkflowError, WorkflowRegistry


class ServiceError(RuntimeError):
    pass


class FilmGraphService:
    def __init__(
        self,
        repository: Repository,
        skills: SkillRegistry,
        workflows: WorkflowRegistry,
        agent: MockAgentProvider,
    ):
        self.repository = repository
        self.skills = skills
        self.workflows = workflows
        self.agent = agent

    def run_skill(
        self,
        *,
        project_id: str,
        skill_name: str,
        input_version_ids: list[str],
    ) -> dict[str, Any]:
        try:
            skill = self.skills.get(skill_name)
            inputs = [self.repository.get_version(version_id) for version_id in input_version_ids]
        except (SkillError, RepositoryError) as exc:
            raise ServiceError(str(exc)) from exc

        if any(item["project_id"] != project_id for item in inputs):
            raise ServiceError("Every input must belong to the requested project")

        permissions = skill.manifest.get("permissions", {}).get("artifacts", {})
        allowed_read = set(permissions.get("read", []))
        input_types = {item["artifact_type"] for item in inputs}
        if not input_types.issubset(allowed_read):
            disallowed = sorted(input_types - allowed_read)
            raise ServiceError(f"Skill is not allowed to read artifact types: {disallowed}")

        try:
            output_type, title, payload = self.agent.run(skill, inputs)
        except AgentError as exc:
            raise ServiceError(str(exc)) from exc

        allowed_propose = set(permissions.get("propose", []))
        if output_type not in allowed_propose:
            raise ServiceError(f"Skill is not allowed to propose artifact type {output_type}")

        artifact = self.repository.create_artifact_with_version(
            project_id=project_id,
            artifact_type=output_type,
            title=title,
            payload=payload,
            status="proposed",
            created_by=f"skill:{skill.name}@{skill.version}",
        )
        output_version = artifact["current_version"]
        for input_item in inputs:
            self.repository.add_edge(
                project_id,
                input_item["artifact_id"],
                artifact["id"],
                "proposed_from",
            )
        run = self.repository.create_skill_run(
            project_id=project_id,
            skill_name=skill.name,
            skill_version=skill.version,
            skill_digest=skill.digest,
            input_version_ids=input_version_ids,
            output_version_id=output_version["id"],
            status="proposed",
            details={
                "provider": "mock",
                "network_calls": 0,
                "approval_capability": False,
                "output_artifact_id": artifact["id"],
            },
        )
        return {"skill_run": run, "output_artifact": artifact}

    def run_workflow(
        self,
        *,
        project_id: str,
        workflow_name: str,
        inputs: dict[str, str],
    ) -> dict[str, Any]:
        try:
            workflow = self.workflows.get(workflow_name)
        except WorkflowError as exc:
            raise ServiceError(str(exc)) from exc

        run = self.repository.create_workflow_run(
            project_id=project_id,
            workflow_name=workflow.name,
            workflow_version=workflow.version,
            inputs=inputs,
        )
        output_version_id: str | None = None

        for step in workflow.plan.get("steps", []):
            step_id = step["id"]
            step_type = step["type"]
            if step_type == "agent_run":
                skill_name = step["skill"]
                version_ids = [
                    inputs["scene_contract_version_id"],
                    inputs["screenplay_scene_version_id"],
                ]
                result = self.run_skill(
                    project_id=project_id,
                    skill_name=skill_name,
                    input_version_ids=version_ids,
                )
                output_version_id = result["output_artifact"]["current_version"]["id"]
                self.repository.add_workflow_step(
                    run["id"], step_id, step_type, "completed", {"output_version_id": output_version_id}
                )
            elif step_type == "validator":
                if output_version_id is None:
                    raise ServiceError("Validator has no upstream proposal")
                payload = self.repository.get_version(output_version_id)["payload"]
                preservation = payload.get("preservation_check", {})
                passed = (
                    preservation.get("scene_outcome_preserved") is True
                    and preservation.get("knowledge_delta_preserved") is True
                    and preservation.get("new_story_facts") == []
                )
                self.repository.add_workflow_step(
                    run["id"], step_id, step_type, "passed" if passed else "failed", {"passed": passed}
                )
                if not passed:
                    return self.repository.update_workflow_run(
                        run["id"], status="blocked", output_version_id=output_version_id
                    )
            elif step_type == "human_approval":
                self.repository.add_workflow_step(
                    run["id"],
                    step_id,
                    step_type,
                    "waiting",
                    {"message": "A human must approve the proposed patch."},
                )
                return self.repository.update_workflow_run(
                    run["id"], status="waiting_for_human", output_version_id=output_version_id
                )
            elif step_type == "emit_artifact":
                self.repository.add_workflow_step(
                    run["id"], step_id, step_type, "deferred", {"reason": "Requires approval"}
                )
            else:
                raise ServiceError(f"Prototype workflow step is unsupported: {step_type}")

        return self.repository.update_workflow_run(
            run["id"], status="completed", output_version_id=output_version_id
        )

    def approve_workflow(
        self,
        run_id: str,
        *,
        actor: str,
        rationale: str,
    ) -> dict[str, Any]:
        try:
            run = self.repository.get_workflow_run(run_id)
        except RepositoryError as exc:
            raise ServiceError(str(exc)) from exc
        if run["status"] != "waiting_for_human" or not run.get("output_version_id"):
            raise ServiceError("Workflow is not awaiting an approvable artifact")
        self.repository.approve_version(run["output_version_id"], actor=actor, rationale=rationale)
        self.repository.add_workflow_step(
            run_id,
            "approval",
            "human_approval",
            "approved",
            {"actor": actor, "rationale": rationale},
        )
        return self.repository.update_workflow_run(run_id, status="completed")
