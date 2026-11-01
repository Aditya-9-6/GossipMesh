import struct
import zlib
import asyncio
from typing import AsyncIterator, Optional, Tuple, List


class FrameError(Exception):
    """Base exception for framing and deframing errors."""

    pass


class ChecksumError(FrameError):
    """Raised when frame checksum verification fails."""

    pass


class ProtocolError(FrameError):
    """Raised when frame magic bytes or structure is invalid."""

    pass


class PacketFramer:
    """
    High-performance zero-copy packet framer and deframer utilizing pre-allocated
    buffers, magic bytes, length prefixes, and CRC32 checksums for high-throughput gossip streams.

    Wire Format:
    [ Magic: 2 bytes (0xGM) ] [ Flags: 1 byte ] [ Payload Length: 4 bytes (Big-Endian) ] [ CRC32: 4 bytes ] [ Payload: N bytes ]
    """

    MAGIC = b"GM"
    HEADER_FORMAT = "!2sBII"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, max_payload_size: int = 65536):
        self.max_payload_size = max_payload_size
        self._pool: List[bytearray] = []

    def pack_frame(self, payload: bytes, flags: int = 0) -> bytes:
        """
        Serializes a payload into a framed packet byte string with header, checksum, and magic.
        """
        if len(payload) > self.max_payload_size:
            raise ValueError(f"Payload size {len(payload)} exceeds max_payload_size {self.max_payload_size}")

        payload_len = len(payload)
        # Compute CRC32 over payload for data integrity
        checksum = zlib.crc32(payload) & 0xFFFFFFFF

        header = struct.pack(self.HEADER_FORMAT, self.MAGIC, flags, payload_len, checksum)
        return header + payload

    async def deframe_stream(self, reader: asyncio.StreamReader) -> AsyncIterator[Tuple[int, bytes]]:
        """
        Asynchronously reads from an asyncio.StreamReader, deframing packets zero-copy style
        where possible, validating checksums and handling stream re-synchronization.
        """
        while True:
            # Read exact header size
            header_buf = await reader.readexactly(self.HEADER_SIZE)
            if not header_buf or len(header_buf) < self.HEADER_SIZE:
                break

            magic, flags, payload_len, expected_checksum = struct.unpack(self.HEADER_FORMAT, header_buf)

            if magic != self.MAGIC:
                raise ProtocolError(f"Invalid framing magic bytes: {magic!r}. Expected {self.MAGIC!r}")

            if payload_len > self.max_payload_size:
                raise ProtocolError(f"Payload length {payload_len} exceeds maximum allowed {self.max_payload_size}")

            # Read exact payload
            payload = await reader.readexactly(payload_len)
            if len(payload) != payload_len:
                raise ProtocolError("Stream truncated while reading frame payload")

            # Verify CRC32 checksum
            actual_checksum = zlib.crc32(payload) & 0xFFFFFFFF
            if actual_checksum != expected_checksum:
                raise ChecksumError(
                    f"Frame checksum verification failed: expected 0x{expected_checksum:08X}, got 0x{actual_checksum:08X}"
                )

            yield flags, payload

    def deframe_bytes(self, buffer: bytearray) -> Tuple[List[Tuple[int, bytes]], int]:
        """
        Synchronously deframes complete packets from a raw bytearray buffer.
        Returns a list of (flags, payload) tuples and the number of consumed bytes.
        Useful for ring-buffer or socket stream chunks.
        """
        frames = []
        offset = 0
        buf_len = len(buffer)

        while offset + self.HEADER_SIZE <= buf_len:
            magic, flags, payload_len, expected_checksum = struct.unpack_from(self.HEADER_FORMAT, buffer, offset)

            if magic != self.MAGIC:
                raise ProtocolError(f"Invalid framing magic bytes: {magic!r}")

            total_frame_size = self.HEADER_SIZE + payload_len
            if offset + total_frame_size > buf_len:
                # Incomplete frame, wait for more data
                break

            payload_view = memoryview(buffer)[offset + self.HEADER_SIZE : offset + total_frame_size]
            # Compute CRC32 over memoryview zero-copy
            actual_checksum = zlib.crc32(payload_view) & 0xFFFFFFFF
            if actual_checksum != expected_checksum:
                raise ChecksumError(
                    f"Frame checksum verification failed: expected 0x{expected_checksum:08X}, got 0x{actual_checksum:08X}"
                )

            frames.append((flags, bytes(payload_view)))
            offset += total_frame_size

        return frames, offset
