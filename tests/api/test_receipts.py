import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_returns_id_and_receipt():
    pytest.skip("TODO: plan this test")


def test_upload_rejects_unsupported_media_type():
    pytest.skip("TODO: plan this test")


def test_export_unknown_id_returns_404():
    pytest.skip("TODO: plan this test")


def test_export_known_id_returns_xlsx():
    pytest.skip("TODO: plan this test")
