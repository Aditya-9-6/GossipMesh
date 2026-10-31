import pytest
from gossipmesh.crypto.epoch import get_current_epoch, get_epoch_bounds, is_epoch_valid


def test_get_current_epoch():
    epoch = get_current_epoch(300)
    assert isinstance(epoch, int)
    assert epoch > 0

    with pytest.raises(ValueError):
        get_current_epoch(0)


def test_get_epoch_bounds():
    start, end = get_epoch_bounds(10, 100)
    assert start == 1000
    assert end == 1100

    with pytest.raises(ValueError):
        get_epoch_bounds(10, -1)


def test_is_epoch_valid():
    current = 100
    assert is_epoch_valid(100, current, 1, 1) is True
    assert is_epoch_valid(99, current, 1, 1) is True
    assert is_epoch_valid(101, current, 1, 1) is True
    assert is_epoch_valid(98, current, 1, 1) is False
    assert is_epoch_valid(102, current, 1, 1) is False

    with pytest.raises(ValueError):
        is_epoch_valid(100, current, -1, 1)
