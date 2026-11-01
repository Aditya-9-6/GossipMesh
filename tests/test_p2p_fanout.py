import pytest
from gossipmesh.p2p.fanout import DynamicFanoutController


def test_dynamic_fanout_controller_happy_path():
    controller = DynamicFanoutController("node-1", base_fanout=4, min_fanout=1, max_fanout=12)
    initial_fanout = controller.compute_fanout()
    assert 1 <= initial_fanout <= 12

    # Simulate poor reachability
    for i in range(10):
        controller.update_peer_feedback(f"peer-{i}", success=False, stratum="edge")

    adjusted_fanout = controller.compute_fanout("edge")
    assert adjusted_fanout > initial_fanout

    metrics = controller.get_metrics()
    assert metrics["node_id"] == "node-1"
    assert "current_fanout" in metrics
    assert "matrix" in metrics
