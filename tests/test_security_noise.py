from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric import x25519
from gossipmesh.security.noise import NoiseXXState


def test_noise_xx_handshake_success() -> None:
    # Initialize initiator and responder static keys
    initiator_static = x25519.X25519PrivateKey.generate()
    responder_static = x25519.X25519PrivateKey.generate()

    initiator = NoiseXXState(is_initiator=True, static_private_key=initiator_static)
    responder = NoiseXXState(is_initiator=False, static_private_key=responder_static)

    # Step 1: Initiator writes message 1
    payload_1 = b"Hello Responder"
    msg_1 = initiator.write_message_1(payload_1)

    received_payload_1 = responder.read_message_1(msg_1)
    assert received_payload_1 == payload_1
    assert responder.remote_e_pub is not None

    # Step 2: Responder writes message 2
    payload_2 = b"Hello Initiator"
    msg_2 = responder.write_message_2(payload_2)

    received_payload_2 = initiator.read_message_2(msg_2)
    assert received_payload_2 == payload_2
    assert initiator.remote_s_pub.public_bytes_raw() == responder_static.public_key().public_bytes_raw()

    # Step 3: Initiator writes message 3
    payload_3 = b"Handshake Complete"
    msg_3 = initiator.write_message_3(payload_3)

    received_payload_3 = responder.read_message_3(msg_3)
    assert received_payload_3 == payload_3
    assert responder.remote_s_pub.public_bytes_raw() == initiator_static.public_key().public_bytes_raw()

    # Step 4: Finalize transport keys
    init_send_key, init_recv_key = initiator.finalize()
    resp_recv_key, resp_send_key = responder.finalize()

    assert init_send_key == resp_recv_key
    assert init_recv_key == resp_send_key
    assert len(init_send_key) == 32


def test_noise_invalid_role_raises() -> None:
    initiator = NoiseXXState(is_initiator=True)

    with pytest.raises(ValueError, match="Only responder can read message 1"):
        initiator.read_message_1(b"dummy")

    with pytest.raises(ValueError, match="Only responder can write message 2"):
        initiator.write_message_2(b"dummy")
