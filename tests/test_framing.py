import unittest
import struct
from gossipmesh.p2p.framing import (
    pack_frame,
    StreamParser,
    InvalidMagicError,
    ChecksumError,
    FrameTooLargeError,
    MAGIC_HEADER,
    compute_crc32c,
)


class TestFraming(unittest.TestCase):
    def test_pack_and_parse_single_frame(self):
        payload = b"Hello, GossipMesh P2P Network!"
        frame = pack_frame(payload)

        parser = StreamParser()
        parser.feed(frame)

        frames = list(parser)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], payload)

    def test_pack_and_parse_multiple_frames(self):
        payloads = [b"packet_one", b"packet_two_with_longer_payload", b""]
        frames = b"".join(pack_frame(p) for p in payloads)

        parser = StreamParser()
        parser.feed(frames)

        parsed_payloads = list(parser)
        self.assertEqual(parsed_payloads, payloads)

    def test_partial_reads_and_streaming(self):
        payload = b"streaming chunk validation test"
        frame = pack_frame(payload)

        parser = StreamParser()

        # Feed byte by byte to simulate fragmented TCP chunks
        for byte in frame[:-1]:
            parser.feed(bytes([byte]))
            with self.assertRaises(StopIteration):
                next(parser)

        # Feed final byte
        parser.feed(bytes([frame[-1]]))
        frames = list(parser)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0], payload)

    def test_invalid_magic_header(self):
        payload = b"bad magic test"
        frame = pack_frame(payload)
        # Corrupt magic
        corrupted_frame = b"BAD1" + frame[4:]

        parser = StreamParser()
        parser.feed(corrupted_frame)

        with self.assertRaises(InvalidMagicError):
            next(parser)

    def test_checksum_error(self):
        payload = b"checksum mismatch test"
        frame = pack_frame(payload)

        # Corrupt last byte (part of checksum)
        corrupted_frame = frame[:-1] + bytes([frame[-1] ^ 0xFF])

        parser = StreamParser()
        parser.feed(corrupted_frame)

        with self.assertRaises(ChecksumError):
            next(parser)

    def test_frame_too_large_packing(self):
        large_payload = b"a" * 100
        with self.assertRaises(FrameTooLargeError):
            pack_frame(large_payload, max_length=10)

    def test_frame_too_large_parsing(self):
        payload = b"a" * 50
        frame = pack_frame(payload, max_length=100)

        parser = StreamParser(max_length=20)
        parser.feed(frame)

        with self.assertRaises(FrameTooLargeError):
            next(parser)


if __name__ == "__main__":
    unittest.main()
