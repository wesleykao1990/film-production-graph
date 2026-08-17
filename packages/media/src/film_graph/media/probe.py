"""Small, offline FFmpeg/ffprobe environment and metadata helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from film_graph.contracts.media import MediaProbeResult, ToolAvailability

from .errors import MediaInputNotFound, MediaProbeError, MediaToolUnavailable

CommandRunner = Callable[..., Any]


def _resolve_executable(executable: str) -> str | None:
    """Resolve a command without starting a process."""

    return shutil.which(executable)


def _version(executable: str, runner: CommandRunner = subprocess.run) -> str | None:
    try:
        completed = runner(
            [executable, "-version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (getattr(completed, "stdout", "") or getattr(completed, "stderr", "") or "").strip()
    if not output:
        return None
    return output.splitlines()[0]


def check_tool(
    name: str,
    executable: str | None = None,
    *,
    runner: CommandRunner = subprocess.run,
) -> ToolAvailability:
    """Report local tool availability without raising for a missing binary."""

    executable = executable or name
    resolved = _resolve_executable(executable)
    if resolved is None:
        return ToolAvailability(
            name=name,
            executable=executable,
            available=False,
            error=f"{executable} executable was not found on PATH",
        )
    version = _version(resolved, runner=runner)
    if version is None:
        return ToolAvailability(
            name=name,
            executable=resolved,
            available=False,
            error=f"{resolved} could not be executed",
        )
    return ToolAvailability(name=name, executable=resolved, available=True, version=version)


def check_ffmpeg(
    *, executable: str = "ffmpeg", runner: CommandRunner = subprocess.run
) -> ToolAvailability:
    return check_tool("ffmpeg", executable, runner=runner)


def check_ffprobe(
    *, executable: str = "ffprobe", runner: CommandRunner = subprocess.run
) -> ToolAvailability:
    return check_tool("ffprobe", executable, runner=runner)


@dataclass(frozen=True, slots=True)
class MediaToolStatus:
    """Combined environment check used by startup diagnostics."""

    ffmpeg: ToolAvailability
    ffprobe: ToolAvailability

    @property
    def available(self) -> bool:
        return self.ffmpeg.available and self.ffprobe.available

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "ffmpeg": self.ffmpeg.as_dict(),
            "ffprobe": self.ffprobe.as_dict(),
        }


def check_media_tools(
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    runner: CommandRunner = subprocess.run,
) -> MediaToolStatus:
    return MediaToolStatus(
        ffmpeg=check_ffmpeg(executable=ffmpeg, runner=runner),
        ffprobe=check_ffprobe(executable=ffprobe, runner=runner),
    )


def _stdout(result: Any) -> str:
    output = getattr(result, "stdout", "")
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output or "")


def probe_media(
    path: str | Path,
    *,
    executable: str = "ffprobe",
    runner: CommandRunner = subprocess.run,
) -> MediaProbeResult:
    """Return ffprobe's structured stream/format metadata.

    A missing local binary is a typed, actionable failure.  M00 does not
    silently invent metadata when media tooling is unavailable.
    """

    media_path = Path(path)
    if not media_path.exists():
        raise MediaInputNotFound(f"media input does not exist: {media_path}")
    if not media_path.is_file():
        raise MediaInputNotFound(f"media input is not a file: {media_path}")
    resolved = _resolve_executable(executable)
    if resolved is None:
        raise MediaToolUnavailable(f"{executable} executable was not found on PATH")
    command: Sequence[str] = (
        resolved,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(media_path),
    )
    try:
        completed = runner(command, capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        raise MediaProbeError(f"ffprobe could not inspect {media_path}") from exc
    return_code = getattr(completed, "returncode", 0)
    raw = _stdout(completed)
    if return_code != 0:
        detail = raw.strip() or str(getattr(completed, "stderr", "") or "").strip()
        raise MediaProbeError(f"ffprobe failed for {media_path}: {detail or 'unknown error'}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MediaProbeError(f"ffprobe returned invalid JSON for {media_path}") from exc
    if not isinstance(payload, dict):
        raise MediaProbeError("ffprobe JSON root must be an object")
    streams = payload.get("streams", [])
    media_format = payload.get("format", {})
    if not isinstance(streams, list) or not isinstance(media_format, dict):
        raise MediaProbeError("ffprobe JSON contains invalid streams or format fields")
    return MediaProbeResult(
        path=str(media_path),
        streams=tuple(stream for stream in streams if isinstance(stream, dict)),
        format=dict(media_format),
    )


# Short aliases make the package pleasant to use while retaining descriptive
# names for API and test code.
probe = probe_media
ffmpeg_status = check_ffmpeg
ffprobe_status = check_ffprobe
