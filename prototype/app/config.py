from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    package_root: Path
    db_path: Path
    seed_path: Path
    skill_root: Path
    workflow_root: Path
    static_dir: Path

    @classmethod
    def default(cls) -> "Settings":
        package_root = Path(__file__).resolve().parents[2]
        prototype_root = package_root / "prototype"
        configured_db = os.environ.get("FPG_PROTOTYPE_DB_PATH", "").strip()
        db_path = (
            Path(configured_db).expanduser().resolve()
            if configured_db
            else prototype_root / ".data" / "film_graph.db"
        )
        return cls(
            package_root=package_root,
            db_path=db_path,
            seed_path=prototype_root / "data" / "seed_project.json",
            skill_root=package_root / "skills",
            workflow_root=package_root / "workflows",
            static_dir=prototype_root / "app" / "static",
        )

    @classmethod
    def for_test(cls, db_path: Path, package_root: Path | None = None) -> "Settings":
        package_root = package_root or Path(__file__).resolve().parents[2]
        prototype_root = package_root / "prototype"
        return cls(
            package_root=package_root,
            db_path=db_path,
            seed_path=prototype_root / "data" / "seed_project.json",
            skill_root=package_root / "skills",
            workflow_root=package_root / "workflows",
            static_dir=prototype_root / "app" / "static",
        )
