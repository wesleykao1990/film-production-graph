"""Repository-wide deterministic test guardrails."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Generator
from typing import Any

import pytest


def _is_loopback(address: Any) -> bool:
    if isinstance(address, str):
        return True  # Unix-domain socket path.
    if not isinstance(address, tuple) or not address:
        return False
    host = address[0]
    try:
        return ipaddress.ip_address(host).is_loopback
    except (TypeError, ValueError):
        return host == "localhost"


@pytest.fixture(autouse=True)
def deny_external_network(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Reject non-loopback sockets in ordinary tests.

    Localhost remains available for explicit API/database integration tests. Tests
    requiring real providers belong in protected manual workflows, never this suite.
    """

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_getaddrinfo = socket.getaddrinfo

    def guarded_connect(sock: socket.socket, address: Any) -> Any:
        if not _is_loopback(address):
            raise RuntimeError(f"external network disabled during tests: {address!r}")
        return original_connect(sock, address)

    def guarded_connect_ex(sock: socket.socket, address: Any) -> int:
        if not _is_loopback(address):
            raise RuntimeError(f"external network disabled during tests: {address!r}")
        return original_connect_ex(sock, address)

    def guarded_getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
        normalized_host = host.decode() if isinstance(host, bytes) else host
        if not _is_loopback((normalized_host, port)):
            raise RuntimeError(f"external DNS disabled during tests: {host!r}")
        return original_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    yield
