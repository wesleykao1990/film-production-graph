"""Make the standalone M00 package sources testable from any cwd."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIRS = (
    ROOT / "apps/api/src",
    ROOT / "packages/domain/src",
    ROOT / "packages/contracts/src",
    ROOT / "packages/application/src",
    ROOT / "packages/model-routing/src",
    ROOT / "packages/provider-contracts/src",
    ROOT / "packages/media/src",
    ROOT / "packages/agent-runtime/src",
    ROOT / "packages/persistence/src",
)
for source_dir in reversed(SOURCE_DIRS):
    source = str(source_dir)
    if source not in sys.path:
        sys.path.insert(0, source)
