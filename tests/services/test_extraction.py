from unittest.mock import MagicMock, patch

import pytest

from app.services.extraction import extract_receipt


def test_extract_receipt_returns_parsed_output(sample_receipt):
    fake_response = MagicMock(parsed_output=sample_receipt)

    with patch(
        "app.services.extraction.client.messages.parse", return_value=fake_response
    ):
        result = extract_receipt(b"fake-image-bytes", "image/jpeg")

    assert result == sample_receipt


def test_extract_receipt_raises_on_none():
    fake_response = MagicMock(parsed_output=None)

    with patch(
        "app.services.extraction.client.messages.parse", return_value=fake_response
    ):
        with pytest.raises(ValueError):
            extract_receipt(b"fake-image-bytes", "image/jpeg")
