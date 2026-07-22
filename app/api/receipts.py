from typing import cast, get_args

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response

from app.models.receipt import Receipt
from app.services.excel_export import receipt_to_excel
from app.services.extraction import SupportedMediaType, extract_receipt
from app.services.session_store import get_receipt, save_receipt

router = APIRouter(tags=["receipts"])

SUPPORTED_MEDIA_TYPES: tuple[SupportedMediaType, ...] = get_args(SupportedMediaType)


@router.get("/receipts")
def list_receipts():
    return []


@router.post("/receipts/upload")
async def upload_receipt(file: UploadFile) -> dict[str, str | Receipt]:
    if file.content_type not in SUPPORTED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported media type: {file.content_type}",
        )

    image_bytes = await file.read()
    media_type = cast(SupportedMediaType, file.content_type)
    receipt = extract_receipt(image_bytes, media_type)
    receipt_id = save_receipt(receipt)

    return {"id": receipt_id, "receipt": receipt}


@router.get("/receipts/{receipt_id}/export")
def export_receipt(receipt_id: str) -> Response:
    receipt = get_receipt(receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")

    excel_bytes = receipt_to_excel(receipt)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{receipt_id}.xlsx"'},
    )
