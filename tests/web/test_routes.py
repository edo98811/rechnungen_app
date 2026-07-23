import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_renders_upload_form():
    pytest.skip("TODO: plan this test")


def test_upload_renders_result_page():
    pytest.skip("TODO: plan this test")
