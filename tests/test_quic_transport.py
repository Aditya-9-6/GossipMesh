"""
Unit tests for Bounded QUIC Datagram Transport with Congestion Control.
"""

import pytest
import asyncio
from gossipmesh.p2p.quic_transport import QUICDatagram, QUICDatagramTransport
from gossipmesh.p2p.congestion import CongestionConfig


def test_quic_datagram_serialization():
    datagram = QUICDatagram(
        datagram_id="test-id-12345678901234567890123456789",
        is_reliable=True,
        sequence_number=42,
        payload=b"Hello QUIC Datagram",
    )

    serialized = datagram.serialize()
    assert isinstance(serialized, bytes)

    deserialized = QUICDatagram.deserialize(serialized)
    assert deserialized.datagram_id == datagram.datagram_id
    assert deserialized.is_reliable == datagram.is_reliable
    assert deserialized.sequence_number == datagram.sequence_number
    assert deserialized.payload == datagram.payload


@pytest.mark.asyncio
async def test_quic_transport_lifecycle_and_sending():
    transport = QUICDatagramTransport(bind_address="127.0.0.1", port=9101)
    await transport.start()
    assert transport._running is True

    transport.register_peer("peer-1", "127.0.0.1", 9200)

    success = await transport.send_datagram("peer-1", b"Ping payload", is_reliable=False)
    assert success is True

    await transport.stop()
    assert transport._running is False


def test_quic_incoming_datagram_handling():
    transport = QUICDatagramTransport()
    datagram = QUICDatagram(
        datagram_id="incoming-id-12345678901234567890123",
        is_reliable=False,
        sequence_number=1,
        payload=b"Test incoming payload",
    )
    raw = datagram.serialize()
    payload = transport.handle_incoming_datagram(raw)
    assert payload == b"Test incoming payload"
