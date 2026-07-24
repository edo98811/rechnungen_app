from io import BytesIO

import openpyxl
from fastapi.testclient import TestClient

from app.main import app
from app.services import session_store

client = TestClient(app)


def test_index_renders_dashboard_shell():
    response = client.get("/")

    assert response.status_code == 200
    assert "reload-btn" in response.text


def test_export_receipts_returns_xlsx_of_selected_only(sample_receipt):
    receipt_id_1 = session_store.save_receipt(sample_receipt)
    session_store.save_receipt(sample_receipt)

    response = client.post(
        "/receipts/export",
        data={"receipt_ids": [receipt_id_1]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    workbook = openpyxl.load_workbook(BytesIO(response.content))
    sheet = workbook.active
    assert sheet is not None
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[0][0] == "product_name"

    item_rows = [r for r in rows if r[0] == sample_receipt.items[0].name]
    # only the selected receipt's single line item should show up, not both
    assert len(item_rows) == 1


def test_export_receipts_with_no_selection_returns_400():
    response = client.post("/receipts/export", data={})

    assert response.status_code == 400
