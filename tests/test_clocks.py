import pytest
import threading
from gossipmesh.core.clocks import VectorClock


def test_vector_clock_basic():
    vc = VectorClock("node-A")
    assert vc.get_time("node-A") == 0
    assert vc.increment() == 1
    assert vc.get_time("node-A") == 1


def test_vector_clock_update():
    vc = VectorClock("node-A", {"node-A": 2, "node-B": 5})
    vc.update({"node-B": 3, "node-C": 10})
    snap = vc.snapshot()
    assert snap["node-A"] == 2
    assert snap["node-B"] == 5
    assert snap["node-C"] == 10


def test_vector_clock_delta_and_view():
    vc = VectorClock("node-A", {"node-A": 5, "node-B": 3})
    known = {"node-A": 3, "node-B": 3, "node-C": 1}
    
    d = vc.delta(known)
    assert d == {"node-A": 5}

    view_items = list(vc.delta_view(known))
    assert view_items == [("node-A", 5)]


def test_vector_clock_comparisons():
    vc = VectorClock("node-A", {"node-A": 2, "node-B": 1})
    
    assert vc.compare({"node-A": 2, "node-B": 1}) == "EQUAL"
    assert vc.compare({"node-A": 3, "node-B": 2}) == "LESS_THAN"
    assert vc.compare({"node-A": 1, "node-B": 1}) == "GREATER_THAN"
    assert vc.compare({"node-A": 2, "node-B": 0}) == "CONCURRENT"


def test_vector_clock_concurrency():
    vc = VectorClock("node-A")
    threads = []
    for _ in range(10):
        t = threading.Thread(target=vc.increment)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    assert vc.get_time("node-A") == 10
