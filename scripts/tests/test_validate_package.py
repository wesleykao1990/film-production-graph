from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_package import is_transient_path  # noqa: E402


class ValidatePackageTests(unittest.TestCase):
    def test_generated_dependency_and_build_paths_are_excluded(self) -> None:
        for relative in (
            ".venv/package.json",
            "node_modules/dependency/package.json",
            "apps/studio-web/.next/manifest.json",
            "packages/domain/src/film_graph_domain.egg-info/PKG-INFO",
            "apps/studio-web/tsconfig.tsbuildinfo",
            "infra/supabase/.temp/project-ref",
        ):
            with self.subTest(relative=relative):
                self.assertTrue(is_transient_path(ROOT / relative))

    def test_source_paths_remain_in_validation_scope(self) -> None:
        self.assertFalse(is_transient_path(ROOT / "schemas/artifact-envelope.schema.json"))
        self.assertFalse(is_transient_path(ROOT / "apps/studio-web/package.json"))


if __name__ == "__main__":
    unittest.main()
