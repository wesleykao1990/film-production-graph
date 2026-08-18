from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from film_graph.skills import (
    SkillLimits,
    SkillLockError,
    SkillRegistry,
    SkillSecurityError,
    SkillValidationError,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "e64ef1e5b33c14dc23cc85e9d6f1b466a99634aa"


def copy_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    shutil.copytree(ROOT / "skills", repository / "skills")
    shutil.copytree(ROOT / "schemas", repository / "schemas")
    shutil.copy2(ROOT / "skills.lock", repository / "skills.lock")
    return repository


def registry(repository: Path, *, limits: SkillLimits | None = None) -> SkillRegistry:
    return SkillRegistry(
        repository_root=repository,
        skill_roots=[Path("skills")],
        lock_path=Path("skills.lock"),
        limits=limits,
    )


def write_yaml(path: Path, value: object) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def refresh_lock(repository: Path) -> None:
    generated = registry(repository).generate_lock(SOURCE_COMMIT)
    write_yaml(repository / "skills.lock", generated)


def test_loads_valid_package_and_exact_lock() -> None:
    loader = registry(ROOT)
    snapshot = loader.reload()
    skill = snapshot.get("subtext-pass")

    assert skill.locked_ref.source_commit == SOURCE_COMMIT
    assert skill.locked_ref.content_hash == (
        "sha256:bc6dac92028b8c9cab9f10baae4df4192f7f14877d1b36d90c93b65e0f24482e"
    )
    assert skill.routing_report.positive_count == 2
    assert skill.routing_report.negative_count == 3
    assert skill.routing_report.adjacent_negative_count == 2
    assert skill.contract_report.case_count == 3
    assert "exposition" in loader.read_resource(
        "subtext-pass", "references/method.md"
    ).lower()
    with pytest.raises(SkillSecurityError, match="not allowlisted"):
        loader.read_resource("subtext-pass", "SKILL.md")


def test_generate_lock_is_deterministic(tmp_path: Path) -> None:
    repository = copy_repository(tmp_path)
    loader = registry(repository)

    assert loader.generate_lock(SOURCE_COMMIT) == loader.generate_lock(SOURCE_COMMIT)
    assert loader.generate_lock(SOURCE_COMMIT)["skills"]["subtext-pass"][
        "content_hash"
    ].startswith("sha256:")


def test_failed_reload_preserves_previous_snapshot_and_detects_reference_drift(
    tmp_path: Path,
) -> None:
    repository = copy_repository(tmp_path)
    loader = registry(repository)
    previous = loader.reload()
    method = repository / "skills/subtext-pass/references/method.md"
    method.write_text(method.read_text(encoding="utf-8") + "\nDrift.\n", encoding="utf-8")

    with pytest.raises(SkillLockError, match="content_hash"):
        loader.reload()

    assert loader.snapshot is previous
    assert loader.snapshot.get("subtext-pass").instructions == previous.get(
        "subtext-pass"
    ).instructions
    with pytest.raises(SkillLockError, match="changed after"):
        loader.read_resource("subtext-pass", "references/method.md")


def test_explicit_reload_adopts_only_new_valid_locked_snapshot(tmp_path: Path) -> None:
    repository = copy_repository(tmp_path)
    loader = registry(repository)
    previous = loader.reload()
    method = repository / "skills/subtext-pass/references/method.md"
    method.write_text(
        method.read_text(encoding="utf-8") + "\nReviewed addition.\n", encoding="utf-8"
    )
    refresh_lock(repository)

    assert loader.snapshot is previous
    current = loader.reload()

    assert current is loader.snapshot
    assert current.snapshot_hash != previous.snapshot_hash
    assert current.get("subtext-pass").locked_ref.content_hash != previous.get(
        "subtext-pass"
    ).locked_ref.content_hash


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("bad-frontmatter", SkillValidationError),
        ("missing-resource", SkillValidationError),
        ("forbidden-tool", SkillSecurityError),
        ("network", SkillSecurityError),
        ("traversal", SkillSecurityError),
    ],
)
def test_rejects_invalid_metadata_permissions_and_paths(
    tmp_path: Path, mutation: str, error: type[Exception]
) -> None:
    repository = copy_repository(tmp_path)
    root = repository / "skills/subtext-pass"
    manifest_path = root / "skill.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if mutation == "bad-frontmatter":
        skill_md = root / "SKILL.md"
        skill_md.write_text(skill_md.read_text(encoding="utf-8").replace("---", "--", 1))
    elif mutation == "missing-resource":
        manifest["resources"]["allow"] = ["references/missing.md"]
        write_yaml(manifest_path, manifest)
    elif mutation == "forbidden-tool":
        manifest["permissions"]["tools"].append("approve_artifact")
        write_yaml(manifest_path, manifest)
    elif mutation == "network":
        manifest["permissions"]["network_hosts"] = ["example.com"]
        write_yaml(manifest_path, manifest)
    else:
        manifest["resources"]["allow"] = ["../outside.md"]
        write_yaml(manifest_path, manifest)

    with pytest.raises(error):
        registry(repository).generate_lock(SOURCE_COMMIT)


@pytest.mark.parametrize("kind", ["symlink", "executable", "code", "shebang"])
def test_rejects_unreviewable_package_content(tmp_path: Path, kind: str) -> None:
    repository = copy_repository(tmp_path)
    root = repository / "skills/subtext-pass"
    if kind == "symlink":
        (root / "linked.md").symlink_to(repository / "skills.lock")
    elif kind == "executable":
        path = root / "executable.txt"
        path.write_text("data", encoding="utf-8")
        path.chmod(0o755)
    elif kind == "code":
        (root / "payload.py").write_text("raise RuntimeError('must never run')\n")
    else:
        (root / "payload.txt").write_text("#!/bin/sh\nexit 1\n")

    with pytest.raises(SkillSecurityError):
        registry(repository).generate_lock(SOURCE_COMMIT)


def test_rejects_size_limits_before_loading(tmp_path: Path) -> None:
    repository = copy_repository(tmp_path)
    with pytest.raises(SkillSecurityError, match="exceeds"):
        registry(
            repository,
            limits=SkillLimits(
                max_files=2,
                max_file_bytes=1024 * 1024,
                max_package_bytes=8 * 1024 * 1024,
            ),
        ).generate_lock(SOURCE_COMMIT)


def test_rejects_missing_extra_and_non_git_lock_entries(tmp_path: Path) -> None:
    repository = copy_repository(tmp_path)
    lock = yaml.safe_load((repository / "skills.lock").read_text(encoding="utf-8"))
    lock["skills"]["subtext-pass"]["source_commit"] = "release-label"
    write_yaml(repository / "skills.lock", lock)
    with pytest.raises(SkillLockError, match="Git SHA"):
        registry(repository).reload()

    lock["skills"] = {}
    write_yaml(repository / "skills.lock", lock)
    with pytest.raises(SkillLockError, match="set mismatch"):
        registry(repository).reload()


def test_contract_fixtures_are_validated_without_execution(tmp_path: Path) -> None:
    repository = copy_repository(tmp_path)
    fixture = repository / "skills/subtext-pass/tests/fixtures/shared-knowledge.json"
    fixture.write_text(json.dumps({"unexpected": True}), encoding="utf-8")

    with pytest.raises(SkillValidationError, match="fails input schema"):
        registry(repository).reload()
