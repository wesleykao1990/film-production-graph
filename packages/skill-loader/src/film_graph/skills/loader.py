"""Strict repository skill loader with atomic explicit reload snapshots."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from film_graph.domain import INITIAL_ARTIFACT_TYPES
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from .errors import SkillLockError, SkillSecurityError, SkillValidationError
from .hashing import PackageFiles, enumerate_package, package_hash
from .models import (
    ContractTestReport,
    LockedSkillRef,
    ResolvedSkill,
    RoutingTestReport,
    SkillLimits,
    SkillSnapshot,
)

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
COMMIT_PATTERN = re.compile(r"^[a-f0-9]{7,40}$")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
ROUTING_THRESHOLD = 0.30

ALLOWED_TOOLS = frozenset(
    {
        "read_artifact",
        "query_edges",
        "retrieve_evidence",
        "read_skill_resource",
        "propose_artifact",
        "propose_patch",
        "report_finding",
    }
)
ALLOWED_PROVIDERS = frozenset({"llm"})
FORBIDDEN_TOOL_MARKERS = (
    "approve",
    "lock",
    "raw_sql",
    "shell",
    "filesystem",
    "secret",
)
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "after",
        "before",
        "for",
        "from",
        "in",
        "its",
        "of",
        "or",
        "the",
        "this",
        "to",
        "use",
        "while",
        "with",
        "without",
    }
)


def _read_yaml(path: Path) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SkillValidationError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise SkillValidationError(f"YAML document must be a mapping: {path}")
    return {str(key): item for key, item in value.items()}


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SkillValidationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise SkillValidationError(f"JSON document must be an object: {path}")
    return {str(key): item for key, item in value.items()}


def _parse_portable(path: Path) -> tuple[Mapping[str, Any], str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SkillValidationError(f"could not read portable skill metadata: {path}") from exc
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise SkillValidationError(f"SKILL.md is missing opening YAML frontmatter: {path}")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise SkillValidationError(f"SKILL.md is missing closing YAML frontmatter: {path}") from exc
    try:
        portable = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as exc:
        raise SkillValidationError(f"invalid SKILL.md frontmatter: {path}: {exc}") from exc
    if not isinstance(portable, Mapping):
        raise SkillValidationError(f"SKILL.md frontmatter must be a mapping: {path}")
    allowed = {"name", "description", "license", "compatibility", "metadata"}
    keys = {str(key) for key in portable}
    if keys != allowed:
        raise SkillValidationError(
            f"SKILL.md portable fields must be exactly {sorted(allowed)}; got {sorted(keys)}"
        )
    metadata = portable.get("metadata")
    if not isinstance(metadata, Mapping):
        raise SkillValidationError("SKILL.md metadata must be a mapping")
    metadata_keys = {str(key) for key in metadata}
    required_metadata = {"version", "film-production-graph-api"}
    if metadata_keys != required_metadata:
        raise SkillValidationError(
            "SKILL.md metadata fields must be version and film-production-graph-api"
        )
    name = portable.get("name")
    description = portable.get("description")
    license_name = portable.get("license")
    compatibility = portable.get("compatibility")
    version = metadata.get("version")
    api_version = metadata.get("film-production-graph-api")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise SkillValidationError("portable skill name is invalid")
    for label, value in (
        ("description", description),
        ("license", license_name),
        ("compatibility", compatibility),
        ("metadata.film-production-graph-api", api_version),
    ):
        if not isinstance(value, str) or not value.strip():
            raise SkillValidationError(f"portable {label} must be a non-empty string")
    if compatibility != "film-production-graph":
        raise SkillValidationError("portable compatibility must be film-production-graph")
    if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
        raise SkillValidationError("portable metadata.version must be major.minor.patch")
    instructions = "\n".join(lines[closing + 1 :]).strip()
    if not instructions:
        raise SkillValidationError("SKILL.md instructions must not be empty")
    return {str(key): item for key, item in portable.items()}, instructions


def _safe_relative_file(
    root: Path, raw: Any, *, label: str, base: Path | None = None
) -> Path:
    if not isinstance(raw, str) or not raw.strip() or "\\" in raw:
        raise SkillSecurityError(f"{label} must be a non-empty POSIX relative path")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise SkillSecurityError(f"{label} escapes the skill package: {raw}")
    candidate = (base or root).joinpath(*pure.parts)
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise SkillValidationError(f"{label} does not exist: {raw}") from exc
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise SkillSecurityError(f"{label} escapes the skill package: {raw}")
    if candidate.is_symlink() or not resolved.is_file():
        raise SkillSecurityError(f"{label} must resolve to a regular reviewed file: {raw}")
    return resolved


def _schema_validator(path: Path) -> Draft202012Validator:
    schema = _read_json(path)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise SkillValidationError(f"invalid Draft 2020-12 schema {path}: {exc}") from exc
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _manifest_errors(manifest: Mapping[str, Any], validator: Draft202012Validator) -> None:
    errors = sorted(validator.iter_errors(manifest), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        where = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise SkillValidationError(f"invalid skill.yaml at {where}: {first.message}")
    if any(key in manifest for key in ("name", "description", "license", "compatibility")):
        raise SkillValidationError("skill.yaml may not duplicate portable metadata")
    permissions = manifest["permissions"]
    if not isinstance(permissions, Mapping):
        raise SkillValidationError("skill permissions must be a mapping")
    tools = permissions["tools"]
    if not isinstance(tools, Sequence) or isinstance(tools, (str, bytes)):
        raise SkillValidationError("skill tools must be a list")
    normalized_tools = {str(tool) for tool in tools}
    forbidden = {
        tool
        for tool in normalized_tools
        if tool not in ALLOWED_TOOLS
        or any(marker in tool.lower() for marker in FORBIDDEN_TOOL_MARKERS)
    }
    if forbidden:
        raise SkillSecurityError(f"skill requests forbidden tools: {sorted(forbidden)}")
    providers = {str(provider) for provider in permissions["providers"]}
    if not providers <= ALLOWED_PROVIDERS:
        raise SkillSecurityError(f"skill requests unsupported providers: {sorted(providers)}")
    if permissions["network_hosts"]:
        raise SkillSecurityError("M02 skills may not request network hosts")
    if permissions["shell"] is not False:
        raise SkillSecurityError("M02 skills may not request shell access")
    artifacts = permissions["artifacts"]
    requested_artifacts = {
        str(item) for item in (*artifacts["read"], *artifacts["propose"])
    }
    unsupported = requested_artifacts - INITIAL_ARTIFACT_TYPES
    if unsupported:
        raise SkillSecurityError(
            f"skill requests unsupported artifact types: {sorted(unsupported)}"
        )


def _stem(token: str) -> str:
    if token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("ed") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 3:
        token = token[:-1]
    if token.endswith("t") and token + "e" in {"rewrite"}:
        return token + "e"
    return token


def _tokens(text: str) -> set[str]:
    return {
        _stem(token)
        for token in TOKEN_PATTERN.findall(text.lower())
        if token not in STOPWORDS and len(token) > 2
    }


def _positive_description(description: str) -> str:
    clauses = re.split(r"(?<=[.!?])\s+", description)
    return " ".join(
        clause
        for clause in clauses
        if "do not use" not in clause.lower() and "not for" not in clause.lower()
    )


def routing_score(name: str, description: str, text: str) -> float:
    normalized_name = name.replace("-", " ").lower()
    if normalized_name in text.lower():
        return 1.0
    profile = _tokens(_positive_description(description))
    candidate = _tokens(text)
    if not candidate:
        return 0.0
    return len(profile & candidate) / min(len(candidate), 8)


def _routing_report(root: Path, path: Path, name: str, description: str) -> RoutingTestReport:
    suite = _read_yaml(path)
    required = {"should_trigger", "should_not_trigger", "adjacent_skill_negatives"}
    if set(suite) != required:
        raise SkillValidationError(f"routing suite must contain exactly {sorted(required)}")

    def inputs(key: str, *, adjacent: bool = False) -> list[str]:
        raw_cases = suite[key]
        if not isinstance(raw_cases, list) or not raw_cases:
            raise SkillValidationError(f"routing suite {key} must be a non-empty list")
        values: list[str] = []
        for case in raw_cases:
            if not isinstance(case, Mapping) or not isinstance(case.get("input"), str):
                raise SkillValidationError(f"routing case in {key} requires string input")
            if adjacent and not isinstance(case.get("skill"), str):
                raise SkillValidationError("adjacent routing cases require a skill name")
            values.append(str(case["input"]))
        return values

    positives = inputs("should_trigger")
    negatives = inputs("should_not_trigger")
    adjacent = inputs("adjacent_skill_negatives", adjacent=True)
    failures = [
        value
        for value in positives
        if routing_score(name, description, value) < ROUTING_THRESHOLD
    ]
    false_positives = [
        value
        for value in (*negatives, *adjacent)
        if routing_score(name, description, value) >= ROUTING_THRESHOLD
    ]
    if failures or false_positives:
        raise SkillValidationError(
            "routing suite failed: "
            f"missed={len(failures)}, false_positive={len(false_positives)}"
        )
    return RoutingTestReport(len(positives), len(negatives), len(adjacent), ROUTING_THRESHOLD)


def _contract_report(
    root: Path, path: Path, input_validator: Draft202012Validator
) -> ContractTestReport:
    suite = _read_yaml(path)
    if set(suite) != {"cases"} or not isinstance(suite["cases"], list) or not suite["cases"]:
        raise SkillValidationError("contract suite requires a non-empty cases list")
    seen: set[str] = set()
    for case in suite["cases"]:
        if not isinstance(case, Mapping):
            raise SkillValidationError("contract cases must be mappings")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise SkillValidationError("contract case ids must be unique non-empty strings")
        seen.add(case_id)
        fixture = _safe_relative_file(
            root,
            case.get("input_fixture"),
            label="contract fixture",
            base=path.parent,
        )
        instance = _read_json(fixture)
        errors = sorted(
            input_validator.iter_errors(instance), key=lambda error: list(error.absolute_path)
        )
        if errors:
            raise SkillValidationError(
                f"contract input fixture {fixture.name} fails input schema: {errors[0].message}"
            )
        expected = case.get("expected")
        if not isinstance(expected, Mapping) or expected.get("status") not in {
            "proposed",
            "blocked",
        }:
            raise SkillValidationError("contract case expected.status must be proposed or blocked")
        if expected["status"] == "proposed" and not isinstance(expected.get("invariants"), list):
            raise SkillValidationError("proposed contract cases require invariants")
        if expected["status"] == "blocked" and not isinstance(
            expected.get("finding_rule"), str
        ):
            raise SkillValidationError("blocked contract cases require finding_rule")
    return ContractTestReport(len(seen))


class SkillRegistry:
    """Holds one immutable resolved snapshot until explicit successful reload."""

    def __init__(
        self,
        *,
        repository_root: Path,
        skill_roots: Sequence[Path],
        lock_path: Path,
        limits: SkillLimits | None = None,
    ) -> None:
        self.repository_root = repository_root.resolve(strict=True)
        self.skill_roots = tuple(skill_roots)
        self.lock_path = lock_path
        self.limits = limits or SkillLimits()
        self._snapshot = SkillSnapshot.empty()

    @property
    def snapshot(self) -> SkillSnapshot:
        return self._snapshot

    def _configured_root(self, raw_root: Path) -> Path:
        candidate = raw_root if raw_root.is_absolute() else self.repository_root / raw_root
        if candidate.is_symlink():
            raise SkillSecurityError(f"configured skill root may not be a symlink: {candidate}")
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise SkillValidationError(
                f"configured skill root does not exist: {candidate}"
            ) from exc
        if self.repository_root not in resolved.parents and resolved != self.repository_root:
            raise SkillSecurityError(f"configured skill root escapes repository: {candidate}")
        if not resolved.is_dir():
            raise SkillValidationError(f"configured skill root is not a directory: {candidate}")
        return resolved

    def _discover(
        self,
    ) -> dict[str, tuple[Path, PackageFiles, Mapping[str, Any], str, Mapping[str, Any]]]:
        discovered: dict[
            str, tuple[Path, PackageFiles, Mapping[str, Any], str, Mapping[str, Any]]
        ] = {}
        for raw_root in self.skill_roots:
            root = self._configured_root(raw_root)
            for directory in sorted(item for item in root.iterdir() if item.is_dir()):
                package = enumerate_package(directory, self.limits)
                skill_md = directory / "SKILL.md"
                manifest_path = directory / "skill.yaml"
                if not skill_md.is_file() or not manifest_path.is_file():
                    raise SkillValidationError(
                        f"skill directory requires SKILL.md and skill.yaml: {directory}"
                    )
                portable, instructions = _parse_portable(skill_md)
                name = str(portable["name"])
                if name in discovered:
                    raise SkillValidationError(f"duplicate portable skill name: {name}")
                manifest = _read_yaml(manifest_path)
                discovered[name] = (directory, package, portable, instructions, manifest)
        if not discovered:
            raise SkillValidationError("configured skill roots contain no skills")
        return discovered

    def _load_lock(self) -> Mapping[str, Mapping[str, Any]]:
        lock_file = (
            self.lock_path
            if self.lock_path.is_absolute()
            else self.repository_root / self.lock_path
        )
        lock = _read_yaml(lock_file)
        schema_path = self.repository_root / "schemas/skills-lock.schema.json"
        validator = _schema_validator(schema_path)
        errors = sorted(validator.iter_errors(lock), key=lambda error: list(error.absolute_path))
        if errors:
            raise SkillLockError(f"invalid skills.lock: {errors[0].message}")
        raw_skills = lock.get("skills")
        if not isinstance(raw_skills, Mapping):
            raise SkillLockError("skills.lock skills must be a mapping")
        return {
            str(name): {str(key): value for key, value in entry.items()}
            for name, entry in raw_skills.items()
            if isinstance(entry, Mapping)
        }

    def _build_snapshot(self) -> SkillSnapshot:
        discovered = self._discover()
        lock = self._load_lock()
        if set(lock) != set(discovered):
            missing = sorted(set(discovered) - set(lock))
            extra = sorted(set(lock) - set(discovered))
            raise SkillLockError(f"skills.lock set mismatch: missing={missing}, extra={extra}")
        manifest_validator = _schema_validator(
            self.repository_root / "schemas/skill-manifest.schema.json"
        )
        resolved_skills: dict[str, ResolvedSkill] = {}
        for name in sorted(discovered):
            directory, package, portable, instructions, manifest = discovered[name]
            _manifest_errors(manifest, manifest_validator)
            contracts = manifest["contracts"]
            input_path = _safe_relative_file(
                directory, contracts["input"], label="input contract"
            )
            output_path = _safe_relative_file(
                directory, contracts["output"], label="output contract"
            )
            input_validator = _schema_validator(input_path)
            _schema_validator(output_path)
            resources = manifest["resources"]
            for raw in resources["allow"]:
                _safe_relative_file(directory, raw, label="allowed resource")
            tests = manifest["tests"]
            routing_path = _safe_relative_file(
                directory, tests["routing"], label="routing test suite"
            )
            contract_path = _safe_relative_file(
                directory, tests["contracts"], label="contract test suite"
            )
            description = str(portable["description"]).strip()
            routing_report = _routing_report(directory, routing_path, name, description)
            contract_report = _contract_report(directory, contract_path, input_validator)
            content_digest = package_hash(directory, package)
            entry = lock[name]
            source_commit = str(entry["source_commit"])
            if not COMMIT_PATTERN.fullmatch(source_commit):
                raise SkillLockError(f"skill {name} source_commit is not a Git SHA")
            source_path = directory.relative_to(self.repository_root).as_posix()
            metadata = portable["metadata"]
            version = str(metadata["version"])
            expected = {
                "source_path": source_path,
                "content_hash": content_digest,
                "metadata_version": version,
            }
            mismatches = [key for key, value in expected.items() if entry.get(key) != value]
            if mismatches:
                raise SkillLockError(f"skill {name} lock mismatch: {sorted(mismatches)}")
            locked_ref = LockedSkillRef(
                name=name,
                source_path=source_path,
                source_commit=source_commit,
                content_hash=content_digest,
                metadata_version=version,
            )
            resolved_skills[name] = ResolvedSkill(
                name=name,
                description=description,
                license=str(portable["license"]),
                compatibility=str(portable["compatibility"]),
                metadata_version=version,
                api_version=str(metadata["film-production-graph-api"]),
                instructions=instructions,
                manifest=manifest,
                locked_ref=locked_ref,
                file_count=len(package.files),
                total_bytes=package.total_bytes,
                routing_report=routing_report,
                contract_report=contract_report,
            )
        snapshot_payload = [
            resolved_skills[name].locked_ref.as_dict() for name in sorted(resolved_skills)
        ]
        encoded = json.dumps(
            snapshot_payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        snapshot_hash = "sha256:" + hashlib.sha256(encoded).hexdigest()
        return SkillSnapshot(snapshot_hash, resolved_skills)

    def reload(self) -> SkillSnapshot:
        """Atomically replace the snapshot only after complete validation succeeds."""

        candidate = self._build_snapshot()
        self._snapshot = candidate
        return candidate

    def generate_lock(self, source_commit: str) -> dict[str, Any]:
        if not COMMIT_PATTERN.fullmatch(source_commit):
            raise SkillLockError("source_commit must be a lowercase Git SHA")
        discovered = self._discover()
        skills: dict[str, dict[str, str]] = {}
        for name in sorted(discovered):
            directory, package, portable, _, manifest = discovered[name]
            manifest_validator = _schema_validator(
                self.repository_root / "schemas/skill-manifest.schema.json"
            )
            _manifest_errors(manifest, manifest_validator)
            contracts = manifest["contracts"]
            input_validator = _schema_validator(
                _safe_relative_file(directory, contracts["input"], label="input contract")
            )
            _schema_validator(
                _safe_relative_file(directory, contracts["output"], label="output contract")
            )
            for raw in manifest["resources"]["allow"]:
                _safe_relative_file(directory, raw, label="allowed resource")
            routing_path = _safe_relative_file(
                directory, manifest["tests"]["routing"], label="routing test suite"
            )
            contract_path = _safe_relative_file(
                directory, manifest["tests"]["contracts"], label="contract test suite"
            )
            _routing_report(
                directory,
                routing_path,
                name,
                str(portable["description"]).strip(),
            )
            _contract_report(directory, contract_path, input_validator)
            metadata = portable["metadata"]
            skills[name] = {
                "source_path": directory.relative_to(self.repository_root).as_posix(),
                "source_commit": source_commit,
                "content_hash": package_hash(directory, package),
                "metadata_version": str(metadata["version"]),
            }
        return {"lock_version": 1, "skills": skills}
