"""
Enterprise Pricing & Model Bundle Configuration
==============================================
Defines the 5 model bundles, pricing tiers, subscription plans,
and task-to-model mapping defaults.
"""

from typing import Dict, Any, List, Optional

# Supported core task types
TASK_SYNTAX = "syntax"
TASK_SECURITY = "security"
TASK_ARCHITECTURE = "architecture"
TASK_AUTO_REMEDIATION = "auto_remediation"

CORE_TASKS = [
    TASK_SYNTAX,
    TASK_SECURITY,
    TASK_ARCHITECTURE,
    TASK_AUTO_REMEDIATION,
]

# 5 Model Bundles based on SOTA Coding Foundation Models (Qwen2.5-Coder & Gemma 2)
MODEL_BUNDLES: Dict[str, Dict[str, Any]] = {
    "b01": {
        "id": "b01",
        "name": "Qwen2.5-Coder-1.5B",
        "family": "Qwen2.5-Coder",
        "parameters": "1.5B",
        "price_per_year": 10_000,
        "description": "Fast syntax, linting & style checking",
        "recommended_tasks": [TASK_SYNTAX],
        "default_dir": "models/b01_qwen2.5_coder_1.5b",
        "vram_min_gb": 4,
    },
    "b02": {
        "id": "b02",
        "name": "Gemma-2-2B / Qwen2.5-Coder-3B",
        "family": "Gemma-2 / Qwen2.5-Coder",
        "parameters": "2B - 3B",
        "price_per_year": 15_000,
        "description": "Medium static analysis, cyclomatic complexity & rule validation",
        "recommended_tasks": [TASK_SYNTAX],
        "default_dir": "models/b02_gemma2_2b_or_qwen3b",
        "vram_min_gb": 6,
    },
    "b03": {
        "id": "b03",
        "name": "Qwen2.5-Coder-7B",
        "family": "Qwen2.5-Coder",
        "parameters": "7B",
        "price_per_year": 25_000,
        "description": "Full-code review, logical correctness, unit test assessment & suggestions",
        "recommended_tasks": [TASK_SECURITY],
        "default_dir": "models/b03_qwen2.5_coder_7b",
        "vram_min_gb": 16,
    },
    "b04": {
        "id": "b04",
        "name": "Qwen2.5-Coder-14B",
        "family": "Qwen2.5-Coder",
        "parameters": "14B",
        "price_per_year": 50_000,  # Flagship $50K Enterprise Tier
        "description": "Enterprise Architecture & Infrastructure Review (Flagship Enterprise Tier)",
        "recommended_tasks": [TASK_SECURITY, TASK_ARCHITECTURE],
        "default_dir": "models/b04_qwen2.5_coder_14b",
        "vram_min_gb": 32,
    },
    "b05": {
        "id": "b05",
        "name": "Qwen2.5-Coder-32B / Gemma-2-27B",
        "family": "Qwen2.5-Coder / Gemma-2",
        "parameters": "27B - 32B",
        "price_per_year": 75_000,  # Heavyweight HFT/Defense Tier
        "description": "Deep code generation, automated vulnerability remediation & air-gapped reasoning",
        "recommended_tasks": [TASK_AUTO_REMEDIATION],
        "default_dir": "models/b05_qwen2.5_coder_32b_or_gemma27b",
        "vram_min_gb": 64,
    },
}

# Subscription plan term multipliers
PLAN_TERMS: Dict[str, float] = {
    "1_year": 1.0,
    "6_months": 0.55,
}

# Default Task-to-Model mapping
DEFAULT_TASK_MODEL_MAP: Dict[str, str] = {
    TASK_SYNTAX: "b01",
    TASK_SECURITY: "b04",
    TASK_ARCHITECTURE: "b04",
    TASK_AUTO_REMEDIATION: "b05",
}


def get_bundle(bundle_id: str) -> Dict[str, Any]:
    """Retrieve bundle metadata by ID."""
    bid = bundle_id.lower().strip()
    if bid not in MODEL_BUNDLES:
        raise ValueError(f"Unknown bundle ID: {bundle_id}. Valid bundles: {list(MODEL_BUNDLES.keys())}")
    return MODEL_BUNDLES[bid]


def calculate_price(
    bundle_ids: List[str],
    plan: str = "1_year",
    task_model_map: Optional[Dict[str, str]] = None,
) -> int:
    """
    Calculate the total subscription price in USD.

    - Single-model mode: price of chosen bundle * plan multiplier.
    - Multi-model / Task-specific mode: sum of unique bundles with a 15% discount for 2+ models.
    """
    if plan not in PLAN_TERMS:
        raise ValueError(f"Unknown plan: {plan}. Valid plans: {list(PLAN_TERMS.keys())}")

    multiplier = PLAN_TERMS[plan]

    # Collect unique bundles
    unique_bundles = set(bid.lower().strip() for bid in bundle_ids)
    if task_model_map:
        for mapped_bid in task_model_map.values():
            unique_bundles.add(mapped_bid.lower().strip())

    if not unique_bundles:
        raise ValueError("At least one bundle ID must be specified.")

    base_total = 0
    for bid in unique_bundles:
        base_total += get_bundle(bid)["price_per_year"]

    # If customer is bundling multiple specialized models, apply a 15% multi-model discount
    if len(unique_bundles) > 1:
        discounted = int(base_total * 0.85)
    else:
        discounted = base_total

    final_price = int(discounted * multiplier)
    return final_price
