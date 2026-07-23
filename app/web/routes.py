from typing import cast, get_args

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.templating import Jinja2Templates

from app.auth import require_login_web
from app.services.extraction import SupportedMediaType, extract_receipt
from app.services.session_store import save_receipt

router = APIRouter(dependencies=[Depends(require_login_web)])
templates = Jinja2Templates(directory="app/templates")

SUPPORTED_MEDIA_TYPES: tuple[SupportedMediaType, ...] = get_args(SupportedMediaType)


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.post("/upload")
async def upload(request: Request, file: UploadFile):
    if file.content_type not in SUPPORTED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported media type: {file.content_type}",
        )

    image_bytes = await file.read()
    media_type = cast(SupportedMediaType, file.content_type)
    receipt = extract_receipt(image_bytes, media_type)
    receipt_id = save_receipt(receipt)

    return templates.TemplateResponse(
        request, "result.html", {"receipt": receipt, "receipt_id": receipt_id}
    )
