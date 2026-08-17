"""Stable errors for optional local media tooling."""


class MediaError(RuntimeError):
    """Base class for media utility failures."""


class MediaToolUnavailable(MediaError):
    """Raised when ffmpeg/ffprobe is not installed or cannot be executed."""


class MediaInputNotFound(MediaError, FileNotFoundError):
    """Raised when a requested local media path does not exist."""


class MediaProbeError(MediaError):
    """Raised when ffprobe returns invalid output or a non-zero status."""
