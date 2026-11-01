import unittest
from gossipmesh.crypto.keys import generate_x25519_keypair
from gossipmesh.crypto.ratchet import DoubleRatchetState, RatchetMessage
from gossipmesh.p2p.secure_transport import SecureMeshTransport


class TestCryptoRatchetAndTransport(unittest.TestCase):
    def test_secure_transport_handshake_and_exchange(self):
        shared_secret = b"0" * 32
        _, alice_pub = generate_x25519_keypair()

        alice = SecureMeshTransport(shared_secret, is_initiator=True, peer_public_bytes=alice_pub)
        bob = SecureMeshTransport(shared_secret, is_initiator=False, peer_public_bytes=alice.ratchet.dh_local_pub)

        plaintext = b"hello gossipmesh secure agent mesh"
        msg = alice.encrypt(plaintext)

        decrypted = bob.decrypt(msg)
        self.assertEqual(plaintext, decrypted)

        # Reply back
        reply_text = b"ack secure agent mesh"
        msg_reply = bob.encrypt(reply_text)
        decrypted_reply = alice.decrypt(msg_reply)
        self.assertEqual(reply_text, decrypted_reply)


if __name__ == "__main":
    unittest.main()
