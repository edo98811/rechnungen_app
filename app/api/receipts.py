from fastapi import APIRouter

router = APIRouter(tags=["receipts"])


@router.get("/receipts")
def list_receipts():
    return []
