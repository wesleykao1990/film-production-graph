from __future__ import annotations

import socket

import pytest


def test_external_network_is_rejected() -> None:
    with socket.socket() as client, pytest.raises(RuntimeError, match="external network disabled"):
        client.connect(("203.0.113.1", 443))


def test_loopback_is_not_classified_as_external() -> None:
    with socket.socket() as client:
        client.settimeout(0.01)
        # A refused local port is acceptable: the guard allowed the connection.
        with pytest.raises((ConnectionRefusedError, TimeoutError, OSError)) as error:
            client.connect(("127.0.0.1", 9))
        assert not isinstance(error.value, RuntimeError)


def test_external_dns_is_rejected_before_resolution() -> None:
    with pytest.raises(RuntimeError, match="external DNS disabled"):
        socket.getaddrinfo("example.com", 443)
