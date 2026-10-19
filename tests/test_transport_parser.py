<<<<<<< HEAD
import asyncio
import unittest
from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.transport import TransportReader

class TestTransportAndParser(unittest.TestCase):

    def test_parser_header_valid(self):
        packet = ZeroCopyPacketParser.serialize_packet(b'X', b'hello world')
        mv = memoryview(packet)
        magic, length = ZeroCopyPacketParser.parse_header(mv)
        self.assertEqual(magic, ZeroCopyPacketParser.MAGIC_BYTE)
        self.assertEqual(length, len(b'hello world'))

    def test_parser_header_invalid_magic(self):
        bad_packet = b'\x99\x00\x00\x00\x05data'
        mv = memoryview(bad_packet)
        with self.assertRaises(ValueError):
            ZeroCopyPacketParser.parse_header(mv)

    def test_parser_header_too_short(self):
        short_packet = b'\x47\x00'
        mv = memoryview(short_packet)
        with self.assertRaises(ValueError):
            ZeroCopyPacketParser.parse_header(mv)

    def test_parser_header_oversized_payload(self):
        # Test security check for oversized payload limit
        oversized_packet = b'\x47' + (100 * 1024 * 1024).to_bytes(4, byteorder='big')
        mv = memoryview(oversized_packet)
        with self.assertRaises(ValueError):
            ZeroCopyPacketParser.parse_header(mv)

    def test_extract_payload(self):
        payload_data = b'test-payload'
        packet = ZeroCopyPacketParser.serialize_packet(b'T', payload_data)
        mv = memoryview(packet)
        _, length = ZeroCopyPacketParser.parse_header(mv)
        payload = ZeroCopyPacketParser.extract_payload(mv, length)
        self.assertEqual(bytes(payload), payload_data)
        self.assertIsInstance(payload, memoryview)

    def test_transport_reader_dispatch(self):
        async def run():
            packet = ZeroCopyPacketParser.serialize_packet(b'A', b'gossip-data')
            
            class MockStreamReader:
                def __init__(self, data):
                    self.data = data
                    self.read_called = False
                async def read(self, n):
                    if not self.read_called:
                        self.read_called = True
                        return self.data
                    return b''

            received = []
            async def dummy_callback(mv: memoryview):
                received.append(bytes(mv))

            stream = MockStreamReader(packet)
            transport = TransportReader(stream, dummy_callback)
            await transport.start_reading()
            
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0], b'gossip-data')

        asyncio.run(run())
=======
import unittest
import asyncio
import struct
from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.transport import TransportSocketReader

class TestZeroCopyParserAndTransport(unittest.TestCase):

    def test_parser_serialization_and_deserialization(self):
        magic = 0x474D4553
        msg_type = 1
        msg_id = "test-msg-uuid-12345678901234567890"
        payload = b"hello gossipmesh zero copy"

        wire_data = ZeroCopyPacketParser.serialize_header(magic, msg_type, msg_id, payload)
        buf = memoryview(wire_data)

        parsed_magic, parsed_type, parsed_id, parsed_len, parsed_payload = ZeroCopyPacketParser.parse_header(buf)

        self.assertEqual(parsed_magic, magic)
        self.assertEqual(parsed_type, msg_type)
        self.assertTrue(parsed_id.startswith("test-msg-uuid"))
        self.assertEqual(parsed_len, len(payload))
        self.assertEqual(bytes(parsed_payload), payload)

    def test_parser_buffer_too_small(self):
        buf = memoryview(b"short")
        with self.assertRaises(ValueError):
            ZeroCopyPacketParser.parse_header(buf)

    def test_transport_socket_reader_valid_packet(self):
        magic = 0x474D4553
        msg_type = 2
        msg_id = "node-uuid-987654321098765432109876"
        payload = b"transport test payload with variable length"
        wire_data = ZeroCopyPacketParser.serialize_header(magic, msg_type, msg_id, payload)

        async def run_test():
            reader = asyncio.StreamReader()
            reader.feed_data(wire_data)
            reader.feed_eof()

            transport_reader = TransportSocketReader(reader, expected_magic=magic)
            res = await transport_reader.read_packet()
            self.assertIsNotNone(res)
            t_type, t_id, t_view = res
            self.assertEqual(t_type, msg_type)
            self.assertTrue(t_id.startswith("node-uuid"))
            self.assertEqual(bytes(t_view), payload)

        asyncio.run(run_test())

    def test_transport_socket_reader_invalid_magic(self):
        magic = 0xBADDEAD
        msg_type = 1
        msg_id = "bad-magic-uuid-123456789012345678"
        wire_data = ZeroCopyPacketParser.serialize_header(magic, msg_type, msg_id, b"payload")

        async def run_test():
            reader = asyncio.StreamReader()
            reader.feed_data(wire_data)
            reader.feed_eof()

            transport_reader = TransportSocketReader(reader, expected_magic=0x474D4553)
            with self.assertRaises(ValueError):
                await transport_reader.read_packet()

        asyncio.run(run_test())
>>>>>>> origin/main

if __name__ == '__main__':
    unittest.main()
