from fastapi import APIRouter

router = APIRouter()


@router.get("/billing")
def get_billing():
    return {"status": "active"}
