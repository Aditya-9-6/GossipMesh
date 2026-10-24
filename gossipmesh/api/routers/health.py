from fastapi import APIRouter
from typing import Dict, str

router = APIRouter()


@router.get("/")
def health_check() -> Dict[str, str]:
    return {"status": "healthy"}
