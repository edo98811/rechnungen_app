from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_renders_upload_form():
    response = client.get("/")

    assert response.status_code == 200
    assert "<form" in response.text.lower()


def test_upload_renders_result_page(sample_receipt):
    with patch("app.web.routes.extract_receipt", return_value=sample_receipt):
        response = client.post(
            "/upload",
            files={"file": ("receipt.jpg", b"fake-bytes", "image/jpeg")},
        )

    assert response.status_code == 200
    assert sample_receipt.store_name in response.text
