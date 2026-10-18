import unittest
from gossipmesh.crypto.keys import KeyPair, derive_hkdf
from gossipmesh.crypto.ratchet import DoubleRatchetSession
from gossipmesh.p2p.secure_transport import SecureP2PTransport

class TestCryptoRatchet(unittest.TestCase):
    def test_keypair_generation(self):
        kp = KeyPair()
        self.assertIsNotNone(kp.private_key)
        self.assertIsNotNone(kp.public_key)
        pub_bytes = kp.public_bytes()
        self.assertEqual(len(pub_bytes), 32)

    def test_hkdf_derivation(self):
        salt = b"test-salt"
        ikm = b"test-secret-material"
        info = b"test-info"
        derived = derive_hkdf(salt, ikm, info, 32)
        self.assertEqual(len(derived), 32)

    def test_double_ratchet_flow(self):
        alice_kp = KeyPair()
        bob_kp = KeyPair()
        
        shared_secret = alice_kp.shared_key(bob_kp.public_key)
        
        alice_session = DoubleRatchetSession.initiate(alice_kp, bob_kp.public_key, shared_secret)
        bob_session = DoubleRatchetSession.initiate(bob_kp, alice_kp.public_key, shared_secret)
        
        plaintext = b"Hello, GossipMesh secure agent mesh!"
        pub_bytes, payload, seq = alice_session.encrypt(plaintext, b"header-ad")
        
        decrypted = bob_session.decrypt(pub_bytes, payload, seq, b"header-ad")
        self.assertEqual(decrypted, plaintext)

    def test_secure_transport(self):
        transport_a = SecureP2PTransport("node-a")
        transport_b = SecureP2PTransport("node-b")
        
        shared_secret = transport_a.keypair.shared_key(transport_b.keypair.public_key)
        
        transport_a.establish_session("node-b", transport_b.keypair.public_bytes(), shared_secret)
        transport_b.establish_session("node-a", transport_a.keypair.public_bytes(), shared_secret)
        
        msg = b"Decentralized gossip message payload"
        pub_bytes, payload, seq = transport_a.send_secure_message("node-b", msg)
        decrypted = transport_b.receive_secure_message("node-a", pub_bytes, payload, seq)
        
        self.assertEqual(msg, decrypted)

if __name__ == "__main__":
    unittest.main()
