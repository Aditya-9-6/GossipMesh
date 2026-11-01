import time
import pytest
from gossipmesh.p2p.causal_barrier import CausalBarrierFilter


def test_causal_barrier_happy_path():
    barrier = CausalBarrierFilter(node_id="node_A", retention_timeout=2.0)
    
    # Message 1 from node_B with clock {"node_B": 1}
    msg1 = {"id": 1, "text": "hello"}
    delivered = barrier.process_message(msg1, {"node_B": 1}, sender_id="node_B")
    
    assert len(delivered) == 1
    assert delivered[0] == msg1
    assert barrier.get_frontier() == {"node_B": 1}


def test_causal_barrier_out_of_order_buffering():
    barrier = CausalBarrierFilter(node_id="node_A", retention_timeout=2.0)
    
    # Message 2 arrives before Message 1 (causal violation)
    msg2 = {"id": 2, "text": "world"}
    delivered2 = barrier.process_message(msg2, {"node_B": 2}, sender_id="node_B")
    assert len(delivered2) == 0
    
    # Now deliver Message 1
    msg1 = {"id": 1, "text": "hello"}
    delivered1 = barrier.process_message(msg1, {"node_B": 1}, sender_id="node_B")
    
    # Both msg1 and msg2 should now be delivered in causal order
    assert len(delivered1) == 2
    assert delivered1[0] == msg1
    assert delivered1[1] == msg2
    assert barrier.get_frontier() == {"node_B": 2}


def test_causal_barrier_retention_timeout():
    barrier = CausalBarrierFilter(node_id="node_A", retention_timeout=0.1)
    
    # Out-of-order message missing predecessor
    msg_late = {"id": 99, "text": "timeout"}
    delivered = barrier.process_message(msg_late, {"node_C": 5}, sender_id="node_C")
    assert len(delivered) == 0
    
    # Wait for timeout to expire
    time.sleep(0.2)
    
    # Trigger cleanup/delivery via another message
    msg_new = {"id": 100, "text": "trigger"}
    delivered_new = barrier.process_message(msg_new, {"node_D": 1}, sender_id="node_D")
    
    # Expired message should be flushed along with the new message
    assert msg_late in delivered_new
    assert msg_new in delivered_new
