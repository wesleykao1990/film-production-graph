"""Opt-in network egress guard for ordinary tests.

The fake implementations do not need this guard to remain offline.  The
context manager is useful for proving that a test fails closed if a future
implementation accidentally reaches for a socket.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

from .errors import NetworkAccessDenied


def _blocked(*_args: Any, **_kwargs: Any) -> Any:
    raise NetworkAccessDenied("network egress is disabled in ordinary tests")


@contextmanager
def network_guard() -> Iterator[None]:
    """Temporarily block common socket entry points and restore them exactly."""

    with (
        patch.object(socket, "socket", _blocked),
        patch.object(socket, "create_connection", _blocked),
        patch.object(socket, "getaddrinfo", _blocked),
    ):
        yield


NetworkGuard = network_guard
