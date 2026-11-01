import pytest
from gossipmesh.consensus.dkg import DKGNode, DistributedKeyGenerationProtocol
from gossipmesh.consensus.vss import VSSScheme


def test_vss_polynomial_and_verification():
    vss = VSSScheme()
    secret = 42
    threshold = 3
    poly = vss.generate_polynomial(secret, threshold)
    assert len(poly) == threshold
    assert poly[0] == secret

    comms = vss.create_commitments(poly)
    assert len(comms) == threshold

    share_x = 1
    share_y = vss.evaluate_polynomial(poly, share_x)
    assert vss.verify_share(share_x, share_y, comms) is True


def test_dkg_protocol_execution():
    total_nodes = 4
    threshold = 2
    nodes = [
        DKGNode(node_id=f"node_{i}", node_index=i + 1, total_nodes=total_nodes, threshold=threshold)
        for i in range(total_nodes)
    ]
    proto = DistributedKeyGenerationProtocol(nodes, threshold)
    success = proto.run_dkg_setup()
    assert success is True
    for node in nodes:
        assert node.collective_public_key is not None
        assert node.node_private_share is not None


if __name__ == "__main__":
    pytest.main([__file__])
