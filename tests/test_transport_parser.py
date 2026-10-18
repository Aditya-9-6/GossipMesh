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

        parsed_magic, parsed_type, parsed_id, parsed_payload = ZeroCopyPacketParser.parse_header(buf)

        self.assertEqual(parsed_magic, magic)
        self.assertEqual(parsed_type, msg_type)
        self.assertTrue(parsed_id.startswith("test-msg-uuid"))
        self.assertEqual(bytes(parsed_payload), payload)

    def test_parser_buffer_too_small(self):
        buf = memoryview(b"short")
        with self.assertRaises(ValueError):
            ZeroCopyPacketParser.parse_header(buf)

    def test_transport_socket_reader_valid_packet(self):
        magic = 0x474D4553
        msg_type = 2
        msg_id = "node-uuid-987654321098765432109876"
        payload = b"transport test payload"
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

        asyncio.run(run_test())

    def test_transport_socket_reader_invalid_magic(self):
        magic = 0xBADDEAD
        msg_type = 1
        msg_id = "bad-magic-uuid-123456789012345678"
        wire_data = ZeroCopyPacketParser.serialize_header(magic, msg_type, msg_id, b"")

        async def run_test():
            reader = asyncio.StreamReader()
            reader.feed_data(wire_data)
            reader.feed_eof()

            transport_reader = TransportSocketReader(reader, expected_magic=0x474D4553)
            with self.assertRaises(ValueError):
                await transport_reader.read_packet()

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
