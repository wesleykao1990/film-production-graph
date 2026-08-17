import pytest
from film_graph.agent_runtime import (
    FakeAgent,
    FakeModel,
    FakeProvider,
    NetworkAccessDenied,
    network_guard,
)
from film_graph.contracts import MediaRequest, ModelRequest


def test_fake_model_is_byte_stable_for_same_request() -> None:
    request = ModelRequest(prompt="write a quiet scene", model="fake-text-v1")
    first = FakeModel(seed="fixed").complete(request)
    second = FakeModel(seed="fixed").complete(request)
    assert first == second
    assert first.metadata["network"] == "disabled"


def test_fake_provider_is_deterministic_and_offline() -> None:
    request = MediaRequest(kind="image", prompt="a blue pen", model="fake-media-v1")
    first = FakeProvider(seed="fixed").generate(request)
    second = FakeProvider(seed="fixed").generate(request)
    assert first.data == second.data
    assert first.request_fingerprint == second.request_fingerprint
    assert first.metadata["network"] == "disabled"


def test_fake_agent_exposes_proposals_but_no_approval_or_lock_capability() -> None:
    agent = FakeAgent()
    proposal = agent.propose("premise_candidate", {"title": "Still Water"})
    assert proposal.status == "proposed"
    assert not hasattr(agent, "approve")
    assert not hasattr(agent, "lock")


def test_network_guard_fails_closed_and_restores_socket() -> None:
    import socket

    original = socket.create_connection
    with network_guard(), pytest.raises(NetworkAccessDenied):
        socket.create_connection(("example.invalid", 443), timeout=0.01)
    assert socket.create_connection is original
