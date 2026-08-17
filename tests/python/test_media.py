from pathlib import Path

import pytest
from film_graph.media import (
    MediaInputNotFound,
    MediaToolUnavailable,
    check_media_tools,
    check_tool,
    probe_media,
)


def test_required_m00_media_tools_are_available() -> None:
    status = check_media_tools()
    assert status.available, status.as_dict()


def test_missing_tool_is_reported_without_running_a_process() -> None:
    status = check_tool("ffprobe", "definitely-not-an-m00-executable")
    assert status.available is False
    assert "not found" in (status.error or "")


def test_probe_missing_input_fails_before_optional_tool_lookup(tmp_path: Path) -> None:
    with pytest.raises(MediaInputNotFound):
        probe_media(tmp_path / "missing.mp4", executable="definitely-not-installed")


def test_probe_reports_unavailable_tool_for_existing_input(tmp_path: Path) -> None:
    media = tmp_path / "fixture.bin"
    media.write_bytes(b"not media")
    with pytest.raises(MediaToolUnavailable):
        probe_media(media, executable="definitely-not-installed")
