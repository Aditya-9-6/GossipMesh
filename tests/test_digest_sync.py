import pytest
from gossipmesh.p2p.digest_sync import DynamicBloomDigestSync


def test_dynamic_bloom_digest_sync_basic():
    sync_node = DynamicBloomDigestSync(initial_capacity=10, base_error_rate=0.01)

    sync_node.add("agent_task_1")
    sync_node.add("agent_task_2")

    assert "agent_task_1" in sync_node
    assert "agent_task_2" in sync_node
    assert "non_existent_task" not in sync_node


def test_dynamic_capacity_expansion():
    # Initialize with tiny capacity to force split/expansion
    sync_node = DynamicBloomDigestSync(initial_capacity=2, base_error_rate=0.01)

    for i in range(15):
        sync_node.add(f"item_{i}")

    for i in range(15):
        assert f"item_{i}" in sync_node


def test_peer_population_tuning():
    sync_node = DynamicBloomDigestSync(initial_capacity=100, base_error_rate=0.01)
    sync_node.add("state_key_alpha")

    # Tune for large peer swarm
    sync_node.tune_for_peer_population(5000)
    assert "state_key_alpha" in sync_node
    assert sync_node.error_rate <= 0.01


def test_reconciliation_flow():
    local_node = DynamicBloomDigestSync(initial_capacity=50, base_error_rate=0.01)
    remote_node = DynamicBloomDigestSync(initial_capacity=50, base_error_rate=0.01)

    local_node.add("shared_key")
    local_node.add("local_only_key")
    remote_node.add("shared_key")

    serialized_remote = remote_node.serialize()
    missing_items = local_node.reconcile(serialized_remote)

    assert "local_only_key" in missing_items
    assert "shared_key" not in missing_items


def test_serialization_roundtrip():
    sync_node = DynamicBloomDigestSync(initial_capacity=100, base_error_rate=0.005)
    sync_node.add("serialized_test_key")
    sync_node.tune_for_peer_population(250)

    ser = sync_node.serialize()
    deser = DynamicBloomDigestSync.deserialize(ser)

    assert "serialized_test_key" in deser
    assert deser.capacity_val >= 100
