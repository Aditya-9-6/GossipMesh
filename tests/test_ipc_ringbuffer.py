import pytest
import multiprocessing
import time
from gossipmesh.p2p.ipc_ringbuffer import IPCSharedMemoryRingBuffer


def test_ipc_ringbuffer_basic_push_pop():
    buffer_name = "test_gossip_ipc_basic"
    ring = IPCSharedMemoryRingBuffer(name=buffer_name, capacity=16, max_msg_size=256, create=True)
    try:
        assert ring.is_empty()
        assert not ring.is_full()

        msg1 = b"agent-gossip-packet-alpha"
        msg2 = b"agent-gossip-packet-beta"

        assert ring.push(msg1) is True
        assert ring.push(msg2) is True
        assert not ring.is_empty()

        popped1 = ring.pop()
        popped2 = ring.pop()

        assert popped1 == msg1
        assert popped2 == msg2
        assert ring.is_empty()
        assert ring.pop() is None
    finally:
        ring.close()
        ring.unlink()


def test_ipc_ringbuffer_capacity_overflow():
    buffer_name = "test_gossip_ipc_overflow"
    # Capacity 4 means max 3 items stored due to ring buffer invariant
    ring = IPCSharedMemoryRingBuffer(name=buffer_name, capacity=4, max_msg_size=64, create=True)
    try:
        assert ring.push(b"msg-1") is True
        assert ring.push(b"msg-2") is True
        assert ring.push(b"msg-3") is True
        assert ring.push(b"msg-4") is False  # Buffer full

        assert ring.pop() == b"msg-1"
        assert ring.push(b"msg-4") is True  # Space freed up
        assert ring.is_full() is True
    finally:
        ring.close()
        ring.unlink()


def _producer_worker(name, num_messages):
    ring = IPCSharedMemoryRingBuffer(name=name, create=False)
    for i in range(num_messages):
        data = f"gossip-payload-{i}".encode("utf-8")
        while not ring.push(data):
            time.sleep(0.0001)
    ring.close()


def _consumer_worker(name, num_messages, output_queue):
    ring = IPCSharedMemoryRingBuffer(name=name, create=False)
    received = 0
    while received < num_messages:
        msg = ring.pop()
        if msg:
            output_queue.put(msg)
            received += 1
        else:
            time.sleep(0.0001)
    ring.close()


def test_ipc_ringbuffer_multiprocess_throughput():
    buffer_name = "test_gossip_ipc_mp"
    num_msgs = 500
    ring = IPCSharedMemoryRingBuffer(name=buffer_name, capacity=128, max_msg_size=256, create=True)
    output_queue = multiprocessing.Queue()

    try:
        producer = multiprocessing.Process(target=_producer_worker, args=(buffer_name, num_msgs))
        consumer = multiprocessing.Process(target=_consumer_worker, args=(buffer_name, num_msgs, output_queue))

        producer.start()
        consumer.start()

        producer.join(timeout=10)
        consumer.join(timeout=10)

        assert not producer.is_alive()
        assert not consumer.is_alive()

        received_msgs = []
        while not output_queue.empty():
            received_msgs.append(output_queue.get_nowait())

        assert len(received_msgs) == num_msgs
        assert received_msgs[0] == b"gossip-payload-0"
        assert received_msgs[-1] == f"gossip-payload-{num_msgs - 1}".encode("utf-8")
    finally:
        ring.close()
        ring.unlink()
