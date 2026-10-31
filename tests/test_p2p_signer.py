import pytest
from gossipmesh.p2p.signer import EpochP2PSigner, EpochP2PVerifier
from gossipmesh.crypto.epoch import get_current_epoch


def test_signer_verifier_happy_path():
    signer = EpochP2PSigner()
    verifier = EpochP2PVerifier(epoch_duration_seconds=300)

    payload = b"hello gossipmesh p2p mesh"
    epoch = get_current_epoch(300)

    signature, bound_epoch = signer.sign_payload(payload, epoch)
    pub_bytes = signer.get_public_bytes()

    is_valid = verifier.verify_payload(pub_bytes, payload, signature, bound_epoch)
    assert is_valid is True


def test_verifier_expired_epoch():
    signer = EpochP2PSigner()
    verifier = EpochP2PVerifier(epoch_duration_seconds=300, drift_past=1, drift_future=1)

    payload = b"replay test payload"
    current_epoch = get_current_epoch(300)
    old_epoch = current_epoch - 5

    signature, bound_epoch = signer.sign_payload(payload, old_epoch)
    pub_bytes = signer.get_public_bytes()

    is_valid = verifier.verify_payload(pub_bytes, payload, signature, bound_epoch)
    assert is_valid is False


def test_verifier_tampered_payload():
    signer = EpochP2PSigner()
    verifier = EpochP2PVerifier()

    payload = b"original payload"
    epoch = get_current_epoch(300)

    signature, bound_epoch = signer.sign_payload(payload, epoch)
    pub_bytes = signer.get_public_bytes()

    is_valid = verifier.verify_payload(pub_bytes, b"tampered payload", signature, bound_epoch)
    assert is_valid is False
