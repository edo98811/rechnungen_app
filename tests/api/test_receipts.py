from io import BytesIO
from unittest.mock import patch

import openpyxl
from fastapi.testclient import TestClient

from app.main import app
from app.services import session_store

client = TestClient(app)


def test_upload_returns_id_and_receipt(sample_receipt):
    with patch(
        "app.api.receipts.extract_receipt", return_value=sample_receipt
    ):
        response = client.post(
            "/api/receipts/upload",
            files={"file": ("receipt.jpg", b"fake-bytes", "image/jpeg")},
        )

    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert body["receipt"]["store_name"] == sample_receipt.store_name
    assert body["receipt"]["total"] == sample_receipt.total


def test_upload_rejects_unsupported_media_type():
    response = client.post(
        "/api/receipts/upload",
        files={"file": ("receipt.txt", b"not-an-image", "text/plain")},
    )

    assert response.status_code == 400


def test_export_unknown_id_returns_404():
    response = client.get("/api/receipts/nonexistent-id/export")

    assert response.status_code == 404


def test_export_known_id_returns_xlsx(sample_receipt):
    receipt_id = session_store.save_receipt(sample_receipt)

    response = client.get(f"/api/receipts/{receipt_id}/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    workbook = openpyxl.load_workbook(BytesIO(response.content))
    assert workbook.active is not None
