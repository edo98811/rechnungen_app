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
def _clear_session_store():
    # app.services.session_store._receipts is a module-level dict acting as
    # an in-memory store. It persists across tests unless cleared here, so
    # every test gets a clean slate before and after running.
    from app.services import session_store

    session_store._receipts.clear()
    yield
    session_store._receipts.clear()
