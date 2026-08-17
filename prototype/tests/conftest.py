from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    package_root = Path(__file__).resolve().parents[2]
    settings = Settings.for_test(tmp_path / "prototype.db", package_root=package_root)
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
