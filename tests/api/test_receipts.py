from io import BytesIO
from unittest.mock import patch

import openpyxl
from fastapi.testclient import TestClient

from app.main import app
from app.services import session_store
from app.services.excel_export import compute_receipt_rows

client = TestClient(app)


def test_list_receipts_returns_saved_receipts(sample_receipt):
    receipt_id_1 = session_store.save_receipt(sample_receipt)
    receipt_id_2 = session_store.save_receipt(sample_receipt)

    response = client.get("/api/receipts")

    assert response.status_code == 200
    body = response.json()
    ids = {entry["id"] for entry in body}
    assert ids == {receipt_id_1, receipt_id_2}
    assert all(
        entry["receipt"]["store_name"] == sample_receipt.store_name for entry in body
    )


def test_preview_receipts_returns_rows_and_grand_total(sample_receipt):
    receipt_id_1 = session_store.save_receipt(sample_receipt)
    receipt_id_2 = session_store.save_receipt(sample_receipt)

    response = client.post(
        "/api/receipts/preview",
        json=[receipt_id_1, receipt_id_2],
    )

    assert response.status_code == 200
    body = response.json()

    stored = [
        session_store.get_receipt(receipt_id_1),
        session_store.get_receipt(receipt_id_2),
    ]
    expected_rows, expected_grand_total = compute_receipt_rows(stored)  # type: ignore[arg-type]

    assert len(body["rows"]) == len(expected_rows)
    assert body["grand_total"] == expected_grand_total
    assert body["rows"][0][0] == sample_receipt.items[0].name


def test_preview_receipts_skips_unknown_ids(sample_receipt):
    receipt_id = session_store.save_receipt(sample_receipt)

    response = client.post(
        "/api/receipts/preview",
        json=[receipt_id, "nonexistent-id"],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["rows"]) == 1


def test_delete_receipts_removes_only_given_ids(sample_receipt):
    receipt_id_1 = session_store.save_receipt(sample_receipt)
    receipt_id_2 = session_store.save_receipt(sample_receipt)

    response = client.post(
        "/api/receipts/delete",
        json=[receipt_id_1, "nonexistent-id"],
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": [receipt_id_1]}
    assert session_store.get_receipt(receipt_id_1) is None
    assert session_store.get_receipt(receipt_id_2) is not None


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
