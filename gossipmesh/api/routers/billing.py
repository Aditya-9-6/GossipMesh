from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def get_billing() -> dict:
    return {"status": "active"}
