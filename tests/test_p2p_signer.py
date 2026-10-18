import unittest
from gossipmesh.p2p.signer import PayloadSigner, PayloadVerifier
from gossipmesh.crypto.epoch import get_current_epoch

class TestP2PSignerVerifier(unittest.TestCase):
    def test_sign_and_verify_success(self):
        signer = PayloadSigner()
        verifier = PayloadVerifier(signer.public_key)

        payload = {"action": "gossip_sync", "node_id": "node-1"}
        envelope = signer.sign_payload(payload)

        self.assertTrue(verifier.verify_envelope(envelope))

    def test_verify_tampered_payload(self):
        signer = PayloadSigner()
        verifier = PayloadVerifier(signer.public_key)

        payload = {"action": "gossip_sync", "node_id": "node-1"}
        envelope = signer.sign_payload(payload)

        envelope["payload"]["node_id"] = "node-malicious"
        self.assertFalse(verifier.verify_envelope(envelope))

    def test_verify_expired_epoch(self):
        signer = PayloadSigner()
        verifier = PayloadVerifier(signer.public_key)

        current_epoch = get_current_epoch()
        old_epoch = current_epoch - 5
        envelope = signer.sign_payload({"data": "test"}, epoch=old_epoch)

        self.assertFalse(verifier.verify_envelope(envelope, tolerance_epochs=1))

if __name__ == "__main__":
    unittest.main()
