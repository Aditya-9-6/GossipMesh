from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter()


@router.get("/")
def list_projects() -> List[Dict[str, Any]]:
    return []
