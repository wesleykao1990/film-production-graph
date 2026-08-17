"""Optional local FFmpeg utilities with explicit unavailable behavior."""

from .errors import MediaError, MediaInputNotFound, MediaProbeError, MediaToolUnavailable
from .probe import (
    MediaToolStatus,
    check_ffmpeg,
    check_ffprobe,
    check_media_tools,
    check_tool,
    ffmpeg_status,
    ffprobe_status,
    probe,
    probe_media,
)

__all__ = [
    "MediaError",
    "MediaInputNotFound",
    "MediaProbeError",
    "MediaToolStatus",
    "MediaToolUnavailable",
    "check_ffmpeg",
    "check_ffprobe",
    "check_media_tools",
    "check_tool",
    "ffmpeg_status",
    "ffprobe_status",
    "probe",
    "probe_media",
]
