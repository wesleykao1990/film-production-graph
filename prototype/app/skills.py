from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class SkillError(RuntimeError):
    pass


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    version: str
    description: str
    digest: str
    source_path: str
    manifest: dict[str, Any]
    instructions: str
    file_count: int

    def public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "digest": self.digest,
            "source_path": self.source_path,
            "file_count": self.file_count,
            "activation": self.manifest.get("activation", "manual"),
            "stage": self.manifest.get("stage"),
            "permissions": self.manifest.get("permissions", {}),
            "budgets": self.manifest.get("budgets", {}),
        }


def parse_skill_markdown(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise SkillError(f"{path} is missing YAML frontmatter")
    _, frontmatter, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter) or {}
    if not isinstance(metadata, dict):
        raise SkillError(f"{path} frontmatter must be a mapping")
    return metadata, body.strip()


def hash_directory(root: Path) -> tuple[str, int]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SkillError(f"Skills may not contain symlinks: {path}")
        if path.is_file() and "__pycache__" not in path.parts:
            files.append(path)
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix().encode("utf-8")):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest(), len(files)


class SkillRegistry:
    def __init__(self, root: Path):
        self.root = root
        self._skills: dict[str, SkillDefinition] = {}

    def load(self) -> None:
        self._skills = {}
        if not self.root.exists():
            return
        for directory in sorted(path for path in self.root.iterdir() if path.is_dir()):
            skill_md = directory / "SKILL.md"
            manifest_path = directory / "skill.yaml"
            if not skill_md.exists() or not manifest_path.exists():
                continue
            portable, instructions = parse_skill_markdown(skill_md)
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            name = str(portable.get("name", "")).strip()
            description = str(portable.get("description", "")).strip()
            version = str((portable.get("metadata") or {}).get("version", "0.0.0"))
            if not name or not description:
                raise SkillError(f"Skill {directory} requires name and description")
            digest, file_count = hash_directory(directory)
            self._skills[name] = SkillDefinition(
                name=name,
                version=version,
                description=description,
                digest=digest,
                source_path=directory.relative_to(self.root.parent).as_posix(),
                manifest=manifest,
                instructions=instructions,
                file_count=file_count,
            )

    def list(self) -> list[SkillDefinition]:
        return [self._skills[name] for name in sorted(self._skills)]

    def get(self, name: str) -> SkillDefinition:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise SkillError(f"Unknown skill: {name}") from exc
