import pytest
import threading
import time
from gossipmesh.p2p.aggregator import AsyncLockFreeRingBufferPacketAggregator


def test_aggregator_basic_push_pop():
    aggregator = AsyncLockFreeRingBufferPacketAggregator(capacity=16, max_msg_size=256, create=True)
    try:
        assert aggregator.push(b"hello gossip") == True
        assert aggregator.push(b"world mesh") == True

        assert aggregator.pop() == b"hello gossip"
        assert aggregator.pop() == b"world mesh"
        assert aggregator.pop() is None
    finally:
        aggregator.close()


def test_aggregator_overflow():
    aggregator = AsyncLockFreeRingBufferPacketAggregator(capacity=4, max_msg_size=64, create=True)
    try:
        # Capacity is 4, usable slots are capacity - 1 = 3
        assert aggregator.push(b"msg1") == True
        assert aggregator.push(b"msg2") == True
        assert aggregator.push(b"msg3") == True
        assert aggregator.push(b"msg4") == False  # Full

        assert aggregator.pop() == b"msg1"
        assert aggregator.push(b"msg4") == True  # Now space is available
    finally:
        aggregator.close()


def test_aggregator_batching():
    aggregator = AsyncLockFreeRingBufferPacketAggregator(capacity=64, max_msg_size=128, create=True)
    try:
        for i in range(10):
            assert aggregator.push(f"payload-{i}".encode()) == True

        batch = aggregator.aggregate_batch(max_batch_size=5)
        assert len(batch) == 5
        assert batch[0] == b"payload-0"
        assert batch[4] == b"payload-4"

        remaining_batch = aggregator.aggregate_batch(max_batch_size=20)
        assert len(remaining_batch) == 5
        assert remaining_batch[0] == b"payload-5"
        assert remaining_batch[4] == b"payload-9"
        assert aggregator.pop() is None
    finally:
        aggregator.close()


def test_concurrent_producer_consumer():
    aggregator = AsyncLockFreeRingBufferPacketAggregator(capacity=1024, max_msg_size=256, create=True)
    num_messages = 200
    errors = []

    def producer():
        try:
            for i in range(num_messages):
                while not aggregator.push(f"msg-{i}".encode()):
                    time.sleep(0.0001)
        except Exception as e:
            errors.append(e)

    def consumer(received_list):
        try:
            count = 0
            while count < num_messages:
                batch = aggregator.aggregate_batch(max_batch_size=16)
                if batch:
                    received_list.extend(batch)
                    count += len(batch)
                else:
                    time.sleep(0.0001)
        except Exception as e:
            errors.append(e)

    received = []
    t_prod = threading.Thread(target=producer)
    t_cons = threading.Thread(target=consumer, args=(received,))

    t_prod.start()
    t_cons.start()

    t_prod.join()
    t_cons.join()

    try:
        assert not errors
        assert len(received) == num_messages
        # Verify contents
        received_set = set(received)
        expected_set = {f"msg-{i}".encode() for i in range(num_messages)}
        assert received_set == expected_set
    finally:
        aggregator.close()
