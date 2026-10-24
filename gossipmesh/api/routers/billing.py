from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()


@router.get("/subscription")
def get_subscription() -> Dict[str, Any]:
    return {"status": "active", "plan": "enterprise"}
