import unittest
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator, encrypt_payload, decrypt_payload


class TestP2PCrypto(unittest.TestCase):
    def test_key_exchange_and_encryption(self):
        alice = EphemeralSessionKeyRotator()
        bob = EphemeralSessionKeyRotator()

        alice_pub = alice.get_public_bytes()
        bob_pub = bob.get_public_bytes()

        alice_key = alice.derive_session_key(bob_pub)
        bob_key = bob.derive_session_key(alice_pub)

        self.assertEqual(alice_key, bob_key)

        msg = b"hello GossipMesh secure p2p channel"
        ciphertext = encrypt_payload(alice_key, msg)
        decrypted = decrypt_payload(bob_key, ciphertext)

        self.assertEqual(msg, decrypted)

    def test_rotation(self):
        rotator = EphemeralSessionKeyRotator()
        priv, pub = rotator.rotate()
        self.assertIsNotNone(pub)
        self.assertIsNone(rotator.session_key)
        self.assertEqual(rotator.message_counter, 0)


if __name__ == "__main__":
    unittest.main()
