import asyncio
import pytest
import zlib
from gossipmesh.p2p.framing import PacketFramer, ChecksumError, ProtocolError


def test_pack_and_deframe_bytes():
    framer = PacketFramer(max_payload_size=1024)
    payload = b"Hello GossipMesh High-Throughput P2P Network!"
    flags = 0x01

    framed = framer.pack_frame(payload, flags=flags)
    assert len(framed) > len(payload)

    buffer = bytearray(framed)
    frames, consumed = framer.deframe_bytes(buffer)

    assert len(frames) == 1
    assert consumed == len(framed)
    assert frames[0][0] == flags
    assert frames[0][1] == payload


def test_deframe_multiple_and_partial_frames():
    framer = PacketFramer(max_payload_size=1024)
    p1 = b"First gossip message"
    p2 = b"Second gossip message"

    f1 = framer.pack_frame(p1, flags=1)
    f2 = framer.pack_frame(p2, flags=2)

    combined = f1 + f2
    buffer = bytearray(combined)

    # Test partial framing (only half of f2 present)
    partial_len = len(f1) + 5
    partial_buffer = buffer[:partial_len]

    frames, consumed = framer.deframe_bytes(partial_buffer)
    assert len(frames) == 1
    assert frames[0][1] == p1
    assert consumed == len(f1)

    # Complete buffer remaining
    remaining = bytearray(buffer[consumed:])
    frames2, consumed2 = framer.deframe_bytes(remaining)
    assert len(frames2) == 1
    assert frames2[0][1] == p2
    assert consumed2 == len(f2)


def test_checksum_error():
    framer = PacketFramer(max_payload_size=1024)
    payload = b"Sensitive gossip payload"
    framed = bytearray(framer.pack_frame(payload))

    # Corrupt payload byte
    framed[-1] ^= 0xFF

    with pytest.raises(ChecksumError):
        framer.deframe_bytes(framed)


def test_protocol_error_magic():
    framer = PacketFramer(max_payload_size=1024)
    framed = bytearray(framer.pack_frame(b"test"))
    # Corrupt magic bytes
    framed[0] = ord("X")
    framed[1] = ord("Y")

    with pytest.raises(ProtocolError):
        framer.deframe_bytes(framed)


@pytest.mark.asyncio
async def test_async_stream_framing():
    framer = PacketFramer(max_payload_size=1024)
    p1 = b"Stream packet A"
    p2 = b"Stream packet B"

    data = framer.pack_frame(p1, flags=10) + framer.pack_frame(p2, flags=20)

    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()

    received = []
    async for flags, payload in framer.deframe_stream(reader):
        received.append((flags, payload))

    assert len(received) == 2
    assert received[0] == (10, p1)
    assert received[1] == (20, p2)
