import pytest
from gossipmesh.p2p.reachability import EpidemicReachabilityMatrix


def test_reachability_matrix_initial_state():
    matrix = EpidemicReachabilityMatrix("node-1")
    assert matrix.average_reachability() == 1.0
    assert matrix.get_peer_metrics("peer-unknown") is None


def test_reachability_matrix_recording():
    matrix = EpidemicReachabilityMatrix("node-1")
    matrix.record_ack("peer-a", success=True, latency=0.05, stratum="core")
    matrix.record_ack("peer-b", success=False, latency=0.50, stratum="edge")

    assert matrix.get_peer_metrics("peer-a")["success_prob"] > 0.5
    assert matrix.stratum_reachability("core") > matrix.stratum_reachability("edge")
    assert matrix.average_reachability() < 1.0
