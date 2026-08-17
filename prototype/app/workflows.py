from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class WorkflowError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    version: str
    source_path: str
    plan: dict[str, Any]

    def public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "source_path": self.source_path,
            "steps": self.plan.get("steps", []),
            "inputs": self.plan.get("inputs", {}),
            "outputs": self.plan.get("outputs", {}),
        }


class WorkflowRegistry:
    def __init__(self, root: Path):
        self.root = root
        self._workflows: dict[str, WorkflowDefinition] = {}

    def load(self) -> None:
        self._workflows = {}
        if not self.root.exists():
            return
        for path in sorted(self.root.glob("*.workflow.yaml")):
            plan = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            name = str(plan.get("name", "")).strip()
            version = str(plan.get("version", "0.0.0"))
            if not name:
                raise WorkflowError(f"Workflow {path} is missing name")
            self._workflows[name] = WorkflowDefinition(
                name=name,
                version=version,
                source_path=path.relative_to(self.root.parent).as_posix(),
                plan=plan,
            )

    def list(self) -> list[WorkflowDefinition]:
        return [self._workflows[name] for name in sorted(self._workflows)]

    def get(self, name: str) -> WorkflowDefinition:
        try:
            return self._workflows[name]
        except KeyError as exc:
            raise WorkflowError(f"Unknown workflow: {name}") from exc
