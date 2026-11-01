import pytest
from gossipmesh.fountain_gossip import (
    FountainConfig,
    Droplet,
    LubyTransformEncoder,
    LubyTransformDecoder,
    HierarchicalAggregationTree,
    TwoPhaseGossipAggregator,
)


def test_droplet_serialization():
    droplet = Droplet(
        session_id="test-session-123",
        droplet_id=42,
        degree=3,
        indices=[1, 5, 9],
        data=b"hello fountain world",
        total_chunks=10,
    )
    raw = droplet.serialize()
    restored = Droplet.deserialize(raw)

    assert restored.session_id == droplet.session_id
    assert restored.droplet_id == droplet.droplet_id
    assert restored.degree == droplet.degree
    assert restored.indices == droplet.indices
    assert restored.data == droplet.data
    assert restored.total_chunks == droplet.total_chunks


def test_luby_transform_codec():
    original_data = b"X" * 4096 + b"Y" * 4096
    config = FountainConfig(chunk_size=512, max_degree=8)
    encoder = LubyTransformEncoder(original_data, config)

    assert encoder.k > 0

    decoder = LubyTransformDecoder(encoder.k, config.chunk_size)
    droplets_generated = 0
    max_attempts = encoder.k * 3

    for i in range(max_attempts):
        droplet = encoder.generate_droplet("codec-test", seed=i)
        # Simulate 10% packet drop loss
        if i % 10 == 0:
            continue
        complete = decoder.add_droplet(droplet)
        droplets_generated += 1
        if complete:
            break

    assert decoder.is_complete()
    reconstructed = decoder.get_reconstructed_state()
    assert reconstructed is not None
    assert reconstructed[: len(original_data)] == original_data


def test_hierarchical_aggregation_tree():
    root = "node-0"
    peers = [f"node-{i}" for i in range(1, 15)]
    tree = HierarchicalAggregationTree(root_id=root, peers=peers, fanout=3)

    assert tree.get_node(root).parent is None
    assert len(tree.get_node(root).children) <= 3

    path = tree.get_path_to_root("node-14")
    assert path[-1] == root
    assert "node-14" in path


def test_two_phase_gossip_aggregator():
    peers = ["node-1", "node-2", "node-3"]
    aggregator = TwoPhaseGossipAggregator(node_id="node-0", peers=peers)

    session_id = "agg-session-99"
    local_state = b"cluster-state-payload"

    # Phase 1: Bottom-up aggregation
    agg_result = aggregator.phase1_aggregate_up(session_id, local_state)
    assert "node-0" in agg_result

    # Phase 2: Top-down fountain dissemination
    droplets = aggregator.phase2_disseminate_down(session_id, local_state)
    assert len(droplets) > 0

    # Feed droplets to aggregator
    completed = False
    for d in droplets:
        if aggregator.receive_droplet(d):
            completed = True
            break

    assert completed
    reconstructed = aggregator.get_reconstructed_state(session_id)
    assert reconstructed is not None
    assert reconstructed[: len(local_state)] == local_state
