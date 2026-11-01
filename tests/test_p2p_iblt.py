import pytest
from gossipmesh.p2p.iblt import InvertibleBloomLookupTable


def test_iblt_basic_insertion_and_lookup():
    iblt = InvertibleBloomLookupTable(size=64, hash_functions=4)
    keys = {10, 20, 30, 40, 50}
    for k in keys:
        iblt.insert(k)

    pos, neg = iblt.list_entries()
    assert pos == keys
    assert len(neg) == 0


def test_iblt_set_reconciliation_difference():
    iblt1 = InvertibleBloomLookupTable(size=128, hash_functions=4)
    iblt2 = InvertibleBloomLookupTable(size=128, hash_functions=4)

    common = {1, 2, 3, 4, 5}
    set1_exclusive = {10, 20, 30}
    set2_exclusive = {100, 200, 300}

    for k in common:
        iblt1.insert(k)
        iblt2.insert(k)
    for k in set1_exclusive:
        iblt1.insert(k)
    for k in set2_exclusive:
        iblt2.insert(k)

    diff = iblt1.subtract(iblt2)
    pos, neg = diff.list_entries()

    assert pos == set1_exclusive
    assert neg == set2_exclusive


def test_iblt_insufficient_capacity_raises():
    iblt = InvertibleBloomLookupTable(size=4, hash_functions=2)
    for k in range(50):
        iblt.insert(k)

    with pytest.raises(ValueError):
        iblt.list_entries()
