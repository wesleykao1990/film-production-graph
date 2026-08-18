"""Canonical, data-only skill package enumeration and hashing."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from .errors import SkillSecurityError
from .models import SkillLimits

TRANSIENT_NAMES = frozenset({".DS_Store"})
TRANSIENT_SUFFIXES = (".swp", ".swo", "~")
CODE_SUFFIXES = frozenset(
    {
        ".bash",
        ".bin",
        ".cjs",
        ".dll",
        ".dylib",
        ".exe",
        ".fish",
        ".jar",
        ".js",
        ".mjs",
        ".ps1",
        ".py",
        ".pyc",
        ".rb",
        ".sh",
        ".so",
        ".ts",
        ".tsx",
        ".wasm",
        ".zsh",
    }
)


@dataclass(frozen=True, slots=True)
class PackageFiles:
    files: tuple[Path, ...]
    total_bytes: int


def should_ignore(path: Path) -> bool:
    return (
        path.name in TRANSIENT_NAMES
        or "__pycache__" in path.parts
        or path.name.endswith(TRANSIENT_SUFFIXES)
    )


def enumerate_package(root: Path, limits: SkillLimits) -> PackageFiles:
    if root.is_symlink():
        raise SkillSecurityError(f"skill root may not be a symlink: {root}")
    if not root.is_dir():
        raise SkillSecurityError(f"skill root is not a directory: {root}")
    files: list[Path] = []
    total_bytes = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SkillSecurityError(f"skill package contains symlink: {path}")
        if not path.is_file() or should_ignore(path):
            continue
        relative = path.relative_to(root)
        if path.suffix.lower() in CODE_SUFFIXES:
            raise SkillSecurityError(f"skill package contains code/script file: {relative}")
        if os.access(path, os.X_OK) or path.stat().st_mode & 0o111:
            raise SkillSecurityError(f"skill package contains executable file: {relative}")
        size = path.stat().st_size
        if size > limits.max_file_bytes:
            raise SkillSecurityError(
                f"skill file exceeds {limits.max_file_bytes} bytes: {relative}"
            )
        with path.open("rb") as handle:
            prefix = handle.read(2)
        if prefix == b"#!":
            raise SkillSecurityError(f"skill package contains shebang content: {relative}")
        files.append(path)
        total_bytes += size
        if len(files) > limits.max_files:
            raise SkillSecurityError(
                f"skill package exceeds {limits.max_files} reviewed files"
            )
        if total_bytes > limits.max_package_bytes:
            raise SkillSecurityError(
                f"skill package exceeds {limits.max_package_bytes} total bytes"
            )
    return PackageFiles(
        tuple(sorted(files, key=lambda item: item.relative_to(root).as_posix().encode("utf-8"))),
        total_bytes,
    )


def package_hash(root: Path, package: PackageFiles) -> str:
    digest = hashlib.sha256()
    for path in package.files:
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()
