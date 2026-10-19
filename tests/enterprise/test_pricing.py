"""
Unit Tests for Enterprise Pricing & Model Bundle Configuration
"""

import pytest
from enterprise.pricing import (
    MODEL_BUNDLES,
    PLAN_TERMS,
    CORE_TASKS,
    DEFAULT_TASK_MODEL_MAP,
    get_bundle,
    calculate_price,
)


def test_bundle_catalog_metadata():
    """Verify all 5 bundles exist with correct parameters and annual pricing."""
    assert len(MODEL_BUNDLES) == 5
    assert "b01" in MODEL_BUNDLES
    assert "b02" in MODEL_BUNDLES
    assert "b03" in MODEL_BUNDLES
    assert "b04" in MODEL_BUNDLES
    assert "b05" in MODEL_BUNDLES

    assert MODEL_BUNDLES["b01"]["price_per_year"] == 10_000
    assert MODEL_BUNDLES["b02"]["price_per_year"] == 15_000
    assert MODEL_BUNDLES["b03"]["price_per_year"] == 25_000
    assert MODEL_BUNDLES["b04"]["price_per_year"] == 50_000  # Flagship
    assert MODEL_BUNDLES["b05"]["price_per_year"] == 75_000  # Defense tier

    assert MODEL_BUNDLES["b04"]["parameters"] == "14B"
    assert MODEL_BUNDLES["b01"]["parameters"] == "1.5B"


def test_get_bundle():
    """Test retrieving bundle details and error handling for unknown IDs."""
    b04 = get_bundle("B04")
    assert b04["name"] == "Qwen2.5-Coder-14B"
    assert b04["price_per_year"] == 50_000

    with pytest.raises(ValueError, match="Unknown bundle ID"):
        get_bundle("b99_nonexistent")


def test_calculate_single_bundle_price():
    """Verify price calculation for single-bundle deployments across annual and 6-month plans."""
    # B04 1-year = $50,000
    price_b04_annual = calculate_price(["b04"], plan="1_year")
    assert price_b04_annual == 50_000

    # B04 6-months = $50,000 * 0.55 = $27,500
    price_b04_6mo = calculate_price(["b04"], plan="6_months")
    assert price_b04_6mo == 27_500

    # B01 1-year = $10,000
    assert calculate_price(["b01"], plan="1_year") == 10_000

    # B05 1-year = $75,000
    assert calculate_price(["b05"], plan="1_year") == 75_000


def test_calculate_multi_bundle_pricing():
    """Verify multi-model task mapping applies the 15% multi-model discount."""
    # B01 ($10k) + B04 ($50k) = $60k base * 0.85 discount = $51,000
    task_map = {"syntax": "b01", "architecture": "b04"}
    price = calculate_price(bundle_ids=["b01", "b04"], plan="1_year", task_model_map=task_map)
    assert price == int(60_000 * 0.85)
    assert price == 51_000


def test_invalid_plan_error():
    """Verify error raised on unsupported subscription plans."""
    with pytest.raises(ValueError, match="Unknown plan"):
        calculate_price(["b04"], plan="2_weeks")
