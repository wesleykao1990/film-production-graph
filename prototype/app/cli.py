from __future__ import annotations

import argparse
import json

from .config import Settings
from .db import Database
from .repository import Repository
from .seed import seed_if_empty
from .skills import SkillRegistry
from .workflows import WorkflowRegistry


def build_runtime():
    settings = Settings.default()
    database = Database(settings.db_path)
    database.initialize()
    repository = Repository(database)
    seed_if_empty(repository, settings.seed_path)
    skills = SkillRegistry(settings.skill_root)
    skills.load()
    workflows = WorkflowRegistry(settings.workflow_root)
    workflows.load()
    return settings, repository, skills, workflows


def main() -> int:
    parser = argparse.ArgumentParser(description="Film Production Graph prototype utility")
    parser.add_argument("command", choices=["reset", "smoke", "show"])
    args = parser.parse_args()

    settings, repository, skills, workflows = build_runtime()
    if args.command == "reset":
        repository.reset()
        seed_if_empty(repository, settings.seed_path)
        print(f"Reset prototype database at {settings.db_path}")
        return 0
    if args.command == "show":
        print(json.dumps(repository.list_lineage("project_blue_pen"), indent=2, ensure_ascii=False))
        return 0
    print(
        json.dumps(
            {
                "database": str(settings.db_path),
                "project_count": repository.project_count(),
                "artifact_count": len(repository.list_artifacts("project_blue_pen")),
                "skills": [skill.name for skill in skills.list()],
                "workflows": [workflow.name for workflow in workflows.list()],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
