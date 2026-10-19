import struct
import zlib

typing_available = True
try:
    import crc32c

    def compute_crc32c(data: bytes) -> int:
        return crc32c.crc32c(data)
except ImportError:

    def compute_crc32c(data: bytes) -> int:
        return zlib.crc32(data) & 0xFFFFFFFF


MAGIC_HEADER = b"GSP1"
HEADER_FORMAT = "!4sI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
CHECKSUM_SIZE = 4


class FramingError(Exception):
    """Base exception for framing or parsing errors."""

    pass


class InvalidMagicError(FramingError):
    """Raised when the packet magic header does not match."""

    pass


class ChecksumError(FramingError):
    """Raised when the packet CRC32C checksum verification fails."""

    pass


class FrameTooLargeError(FramingError):
    """Raised when the packet payload length exceeds maximum allowed bounds."""

    pass


def pack_frame(payload: bytes, max_length: int = 10485760) -> bytes:
    """
    Packs a payload into a zero-copy friendly frame format:
    [4-byte Magic: 'GSP1'] [4-byte Big-Endian Length] [Payload bytes] [4-byte CRC32C Checksum]
    """
    length = len(payload)
    if length > max_length:
        raise FrameTooLargeError(f"Payload length {length} exceeds maximum allowed {max_length}")

    header = struct.pack(HEADER_FORMAT, MAGIC_HEADER, length)
    frame_data_for_crc = header + payload
    checksum = compute_crc32c(frame_data_for_crc)
    checksum_bytes = struct.pack("!I", checksum)

    return header + payload + checksum_bytes


class StreamParser:
    """
    Stateful zero-copy stream parser handling partial TCP reads safely using memoryviews.
    """

    def __init__(self, max_length: int = 10485760):
        self.buffer = bytearray()
        self.max_length = max_length

    def feed(self, data: bytes):
        if data:
            self.buffer.extend(data)

    def __iter__(self):
        return self

    def __next__(self) -> bytes:
        """
        Attempts to parse the next complete frame from the stream buffer.
        Raises StopIteration if no complete frame is available yet.
        """
        total_buffered = len(self.buffer)
        min_frame_size = HEADER_SIZE + CHECKSUM_SIZE

        if total_buffered < min_frame_size:
            raise StopIteration

        mv = memoryview(self.buffer)

        # Verify Magic Header
        magic = mv[:4].tobytes()
        if magic != MAGIC_HEADER:
            raise InvalidMagicError(f"Invalid magic header received: {magic!r}")

        # Parse Length
        length_bytes = mv[4:HEADER_SIZE].tobytes()
        (length,) = struct.unpack("!I", length_bytes)

        if length > self.max_length:
            raise FrameTooLargeError(f"Parsed payload length {length} exceeds maximum allowed {self.max_length}")

        total_needed = HEADER_SIZE + length + CHECKSUM_SIZE
        if total_buffered < total_needed:
            raise StopIteration

        # Extract payload and checksum as bytes immediately to release memoryview exports
        payload_bytes = mv[HEADER_SIZE : HEADER_SIZE + length].tobytes()
        checksum_bytes_val = mv[HEADER_SIZE + length : total_needed].tobytes()

        (received_checksum,) = struct.unpack("!I", checksum_bytes_val)

        # Compute checksum over header + payload
        header_and_payload = mv[: HEADER_SIZE + length].tobytes()
        calculated_checksum = compute_crc32c(header_and_payload)

        if received_checksum != calculated_checksum:
            raise ChecksumError(
                f"CRC32C checksum mismatch: received {received_checksum:#x}, calculated {calculated_checksum:#x}"
            )

        # Release memoryview explicitly before buffer mutation
        del mv

        # Consume the parsed frame from the internal buffer safely
        del self.buffer[:total_needed]

        return payload_bytes
