from __future__ import annotations

import pytest
from gossipmesh.p2p.minhash import MinHashSketch
from gossipmesh.p2p.clustering import PeerTopologyClustering


def test_clustering_workflow():
    clustering = PeerTopologyClustering(similarity_threshold=0.3, num_perm=64)

    s1 = MinHashSketch(num_perm=64)
    s1.update_batch(["peer_a_topic", "shared_topic"])

    s2 = MinHashSketch(num_perm=64)
    s2.update_batch(["peer_b_topic", "shared_topic"])

    s3 = MinHashSketch(num_perm=64)
    s3.update_batch(["completely_isolated_topic"])

    clustering.register_peer("node-A", s1)
    clustering.register_peer("node-B", s2)
    clustering.register_peer("node-C", s3)

    clusters = clustering.cluster_peers()
    assert len(clusters) >= 2

    query = MinHashSketch(num_perm=64)
    query.update("shared_topic")
    best_peer, sim = clustering.find_nearest_cluster_centroid(query)
    assert best_peer in ("node-A", "node-B")
    assert sim >= 0.0


def test_clustering_errors():
    clustering = PeerTopologyClustering()
    with pytest.raises(KeyError):
        clustering.compute_similarity("nonexistent_1", "nonexistent_2")
