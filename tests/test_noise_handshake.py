import unittest
import asyncio
from cryptography.hazmat.primitives.asymmetric import x25519
from gossipmesh.crypto.noise import NoiseHandshakeState
from gossipmesh.p2p.secure_transport import SecureTransport


class TestNoiseHandshake(unittest.TestCase):
    def test_noise_handshake_flow(self):
        async def run():
            priv_a = x25519.X25519PrivateKey.generate()
            priv_b = x25519.X25519PrivateKey.generate()
            
            initiator = NoiseHandshakeState(True, priv_a)
            responder = NoiseHandshakeState(False, priv_b)
            
            initiator.remote_s_pub = priv_b.public_key()
            responder.remote_s_pub = priv_a.public_key()
            
            msg1 = initiator.write_message_1()
            responder.read_message_1(msg1)
            
            msg2 = responder.write_message_2()
            initiator.read_message_2(msg2)
            
            msg3 = initiator.write_message_3()
            responder.read_message_3(msg3)
            
            self.assertIsNotNone(initiator.key)
            self.assertEqual(initiator.key, responder.key)
            
            pt = b"hello gossipmesh p2p"
            ct = initiator.encrypt_and_hash(pt)
            decrypted = responder.decrypt_and_hash(ct)
            self.assertEqual(pt, decrypted)

        asyncio.run(run())

    def test_secure_transport_stream(self):
        async def run():
            priv_a = x25519.X25519PrivateKey.generate()
            priv_b = x25519.X25519PrivateKey.generate()
            
            async def handle_echo(reader, writer):
                transport_b = SecureTransport(reader, writer, priv_b, False)
                transport_b.state.remote_s_pub = priv_a.public_key()
                await transport_b.handshake()
                data = await transport_b.recv()
                await transport_b.send(data)
                writer.close()
                await writer.wait_closed()

            server = await asyncio.start_server(handle_echo, "127.0.0.1", 0)
            addr = server.sockets[0].getsockname()
    
            reader_a, writer_a = await asyncio.open_connection(addr[0], addr[1])
            transport_a = SecureTransport(reader_a, writer_a, priv_a, True)
            transport_a.state.remote_s_pub = priv_b.public_key()
    
            await transport_a.handshake()
            await transport_a.send(b"ping encrypted")
            resp = await transport_a.recv()
            self.assertEqual(resp, b"ping encrypted")
    
            writer_a.close()
            await writer_a.wait_closed()
            server.close()
            await server.wait_closed()
    
        asyncio.run(run())
