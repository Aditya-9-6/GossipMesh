import asyncio
import pytest

from gossipmesh.p2p.trampoline import PeerConnectionTrampoline, ConnectionState


@pytest.mark.asyncio
async def test_trampoline_initial_state():
    trampoline = PeerConnectionTrampoline()
    peer_id = "peer-node-1"

    state = await trampoline.get_state(peer_id)
    assert state == ConnectionState.IDLE
    assert await trampoline.can_dial(peer_id) is True


@pytest.mark.asyncio
async def test_trampoline_success_flow():
    trampoline = PeerConnectionTrampoline()
    peer_id = "peer-node-2"

    async def mock_dial(pid: str) -> bool:
        return True

    success = await trampoline.dial_with_trampoline(peer_id, mock_dial)
    assert success is True
    assert await trampoline.get_state(peer_id) == ConnectionState.CONNECTED
    assert await trampoline.can_dial(peer_id) is False


@pytest.mark.asyncio
async def test_trampoline_backoff_flow():
    trampoline = PeerConnectionTrampoline(base_backoff=0.1, max_backoff=1.0, max_retries=3)
    peer_id = "peer-node-3"

    async def mock_dial(pid: str) -> bool:
        return False

    # Attempt 1 -> Fail, enters BACKOFF
    success = await trampoline.dial_with_trampoline(peer_id, mock_dial)
    assert success is False
    assert await trampoline.get_state(peer_id) == ConnectionState.BACKOFF

    # Immediate redial should be rejected due to backoff delay
    assert await trampoline.can_dial(peer_id) is False
    success_retry = await trampoline.dial_with_trampoline(peer_id, mock_dial)
    assert success_retry is False


@pytest.mark.asyncio
async def test_trampoline_max_retries_failure():
    trampoline = PeerConnectionTrampoline(base_backoff=0.01, max_retries=2)
    peer_id = "peer-node-4"

    async def mock_dial(pid: str) -> bool:
        return False

    # Force attempts up to max_retries
    trampoline._attempts[peer_id] = 2
    await trampoline.set_state(peer_id, ConnectionState.BACKOFF)

    # Exceeded max retries should lead to FAILED state
    state, delay = await trampoline.record_failure(peer_id)
    assert state == ConnectionState.FAILED
    assert await trampoline.get_state(peer_id) == ConnectionState.FAILED
    assert await trampoline.can_dial(peer_id) is False


@pytest.mark.asyncio
async def test_trampoline_reset():
    trampoline = PeerConnectionTrampoline()
    peer_id = "peer-node-5"

    await trampoline.set_state(peer_id, ConnectionState.FAILED)
    trampoline._attempts[peer_id] = 5

    await trampoline.reset(peer_id)
    assert await trampoline.get_state(peer_id) == ConnectionState.IDLE
    assert await trampoline.can_dial(peer_id) is True
