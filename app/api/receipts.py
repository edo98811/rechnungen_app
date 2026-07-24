from typing import cast, get_args

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response

from app.auth import require_login_api
from app.models.receipt import Receipt
from app.services.excel_export import compute_receipt_rows, receipt_to_excel
from app.services.extraction import SupportedMediaType, extract_receipt
from app.services.session_store import (
    delete_receipt,
    get_receipt,
    list_receipts,
    save_receipt,
)

router = APIRouter(tags=["receipts"], dependencies=[Depends(require_login_api)])

SUPPORTED_MEDIA_TYPES: tuple[SupportedMediaType, ...] = get_args(SupportedMediaType)


@router.get("/receipts")
def list_all_receipts():
    return [
        {"id": receipt_id, "receipt": receipt}
        for receipt_id, receipt in list_receipts()
    ]


@router.post("/receipts/upload")
async def upload_receipt(file: UploadFile) -> dict[str, str | Receipt]:
    if file.content_type not in SUPPORTED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported media type: {file.content_type}",
        )

    image_bytes = await file.read()
    media_type = cast(SupportedMediaType, file.content_type)
    try:
        receipt = extract_receipt(image_bytes, media_type)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
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


@router.post("/receipts/delete")
def delete_receipts(ids: list[str]) -> dict:
    deleted = [receipt_id for receipt_id in ids if delete_receipt(receipt_id)]
    return {"deleted": deleted}


@router.post("/receipts/preview")
def preview_receipts(ids: list[str]) -> dict:
    receipts = [
        receipt for receipt_id in ids if (receipt := get_receipt(receipt_id)) is not None
    ]
    rows, grand_total = compute_receipt_rows(receipts)
    return {"rows": rows, "grand_total": grand_total}
