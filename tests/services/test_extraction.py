from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.services.extraction import extract_receipt


def test_extract_receipt_returns_parsed_output(sample_receipt, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    fake_response = MagicMock(text=sample_receipt.model_dump_json())

    with patch(
        "app.services.extraction.client.models.generate_content",
        return_value=fake_response,
    ):
        result = extract_receipt(b"fake-image-bytes", "image/jpeg")

    assert result == sample_receipt


def test_extract_receipt_raises_on_none(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    fake_response = MagicMock(text=None)

    with patch(
        "app.services.extraction.client.models.generate_content",
        return_value=fake_response,
    ):
        with pytest.raises(ValueError, match="did not return a parsed receipt"):
            extract_receipt(b"fake-image-bytes", "image/jpeg")


def test_extract_receipt_fills_missing_date_with_today(sample_receipt, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    unidentified = sample_receipt.model_copy(update={"date": "N/A"})
    fake_response = MagicMock(text=unidentified.model_dump_json())

    with patch(
        "app.services.extraction.client.models.generate_content",
        return_value=fake_response,
    ):
        result = extract_receipt(b"fake-image-bytes", "image/jpeg")

    assert result.date == date.today().isoformat()


def test_extract_receipt_raises_on_missing_api_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")

    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        extract_receipt(b"fake-image-bytes", "image/jpeg")
