import pytest
import asyncio
from gossipmesh.sync.delta import DeltaSyncEngine


@pytest.mark.asyncio
async def test_delta_sync_flow():
    engine1 = DeltaSyncEngine(node_id="nodeA", max_causal_entries=50)
    engine2 = DeltaSyncEngine(node_id="nodeB", max_causal_entries=50)

    vc1 = await engine1.update_state("key1", "value_a")

    # Engine 2 asks for delta with empty clock
    delta = await engine2.get_delta(engine2.local_clock.to_dict())
    # Since engine2 has nothing, engine1 should send all or nothing? Wait, get_delta is called on engine1 with engine2's clock.
    delta = await engine1.get_delta(engine2.local_clock.to_dict())
    assert "key1" in delta

    merged = await engine2.merge_delta(delta)
    assert "key1" in merged
    assert engine2.state_store["key1"][0] == "value_a"


@pytest.mark.asyncio
async def test_concurrent_delta_computation():
    engine = DeltaSyncEngine(node_id="nodeA")
    await engine.update_state("k1", "v1")
    delta = await engine.compute_delta_concurrent({"nodeB": 5})
    assert "k1" in delta
