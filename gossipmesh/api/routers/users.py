from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User

router = APIRouter()

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool

@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return current_user
