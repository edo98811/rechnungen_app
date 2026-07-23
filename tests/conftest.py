import pytest

from app.models.receipt import Receipt, ReceiptItem


@pytest.fixture
def sample_receipt() -> Receipt:
    """A minimal Receipt fixture for use across service/api/web tests."""
    return Receipt(
        store_name="Test Store",
        date="2026-07-23",
        items=[
            ReceiptItem(name="Apples", quantity=2, unit_price=1.5, total_price=3.0),
        ],
        subtotal=3.0,
        tax_amount=0.21,
        total=3.21,
    )


@pytest.fixture(autouse=True)
def _isolated_session_store(tmp_path, monkeypatch):
    # session_store is now SQLite-backed (see
    # app/services/session_store.py) and reads settings.database_path
    # fresh on every call, so pointing it at a per-test tmp file is enough
    # to give every test a clean, isolated store without any explicit
    # clearing/teardown.
    from app.config import settings

    monkeypatch.setattr(
        settings, "database_path", str(tmp_path / "test_session_store.db")
    )
    yield
