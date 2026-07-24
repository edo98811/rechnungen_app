from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from app.auth import require_login_web
from app.services.excel_export import combine_receipts_to_excel
from app.services.session_store import get_receipt

router = APIRouter(dependencies=[Depends(require_login_web)])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "receipts_list.html")


@router.post("/receipts/export")
def export_receipts(receipt_ids: list[str] = Form(default=[])) -> Response:
    receipts = [
        (receipt_id, receipt)
        for receipt_id in receipt_ids
        if (receipt := get_receipt(receipt_id)) is not None
    ]
    if not receipts:
        raise HTTPException(status_code=400, detail="No receipts selected")

    excel_bytes = combine_receipts_to_excel(receipts)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="receipts-combined.xlsx"'
        },
    )
