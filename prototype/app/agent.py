from __future__ import annotations

from typing import Any

from .skills import SkillDefinition


class AgentError(RuntimeError):
    pass


class MockAgentProvider:
    """Deterministic provider used only by the reference prototype.

    It demonstrates permission boundaries and typed proposals without making
    any network or model call. The production implementation replaces this
    provider in M03 while keeping the same application-owned tool boundary.
    """

    def run(self, skill: SkillDefinition, inputs: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
        if skill.name == "subtext-pass":
            return self._run_subtext_pass(skill, inputs)
        return self._run_generic_finding(skill, inputs)

    @staticmethod
    def _run_subtext_pass(
        skill: SkillDefinition, inputs: list[dict[str, Any]]
    ) -> tuple[str, str, dict[str, Any]]:
        by_type = {item["artifact_type"]: item for item in inputs}
        scene_contract = by_type.get("scene_contract")
        screenplay_scene = by_type.get("screenplay_scene")
        if scene_contract is None or screenplay_scene is None:
            raise AgentError("subtext-pass requires scene_contract and screenplay_scene inputs")

        source_lines = screenplay_scene["payload"].get("lines", [])
        replacements = {
            "L01": "The blue dries faster than black.",
            "L02": "Not on this paper.",
            "L03": "It is the page they gave me.",
            "L04": "They stopped stocking this weight in March.",
            "L05": "Sign it, Ivo.",
            "L06": "Your brother never touched the file?",
            "L07": "He never saw it.",
            "L08": "Then you will not mind the ink on my cuff.",
        }
        changes: list[dict[str, Any]] = []
        for line in source_lines:
            line_id = line.get("line_id")
            if line_id in replacements and line.get("text") != replacements[line_id]:
                changes.append(
                    {
                        "operation": "replace_line",
                        "line_id": line_id,
                        "speaker": line.get("speaker"),
                        "before": line.get("text", ""),
                        "after": replacements[line_id],
                        "reason": "Replace direct explanation with tactic, object use, or knowledge pressure.",
                    }
                )

        payload = {
            "patch_id": "PATCH-S07-SUBTEXT-PROTOTYPE",
            "scene_id": screenplay_scene["payload"].get("scene_id", "S07"),
            "source_scene_version_id": screenplay_scene["id"],
            "scene_contract_version_id": scene_contract["id"],
            "skill": {
                "name": skill.name,
                "version": skill.version,
                "digest": skill.digest,
            },
            "scope": {"line_ids": [change["line_id"] for change in changes]},
            "changes": changes,
            "preservation_check": {
                "scene_outcome_preserved": True,
                "knowledge_delta_preserved": True,
                "setup_payoff_links_preserved": True,
                "new_story_facts": [],
            },
            "approval_required": True,
            "prototype_note": "Deterministic mock output; no external model was called.",
        }
        return "screenplay_patch", "Subtext patch for Scene S07", payload

    @staticmethod
    def _run_generic_finding(
        skill: SkillDefinition, inputs: list[dict[str, Any]]
    ) -> tuple[str, str, dict[str, Any]]:
        payload = {
            "skill": {"name": skill.name, "version": skill.version, "digest": skill.digest},
            "input_version_ids": [item["id"] for item in inputs],
            "finding": "The prototype discovered this skill but has no deterministic handler for it.",
            "next_step": "Connect the production PydanticAI runtime in M03 or add a reviewed prototype handler.",
            "approval_required": True,
        }
        return "critic_finding", f"Prototype finding from {skill.name}", payload
