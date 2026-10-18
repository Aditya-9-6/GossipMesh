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

if __name__ == '__main__':
    unittest.main()
