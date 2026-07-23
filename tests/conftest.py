import os

# Must run before app.main (and therefore app.config.settings) is imported
# by any test module — main.py raises at import time if SESSION_SECRET_KEY
# is unset, which would otherwise make the whole suite uncollectible
# whenever a real .env isn't present (fresh clone, CI, etc.).
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-not-for-production")

import pytest

from app.auth import require_login_api, require_login_web
from app.main import app
from app.models.receipt import Receipt, ReceiptItem


@pytest.fixture
def bypass_auth():
    """Bypass require_login_web / require_login_api via dependency overrides.

    Not autouse here — test_auth.py specifically exercises the real
    auth-required behavior and must not have it short-circuited. Route
    tests (tests/api/, tests/web/) opt in automatically via the nested
    autouse fixtures in their own conftest.py that depend on this one.
    """
    app.dependency_overrides[require_login_web] = lambda: None
    app.dependency_overrides[require_login_api] = lambda: None
    yield
    app.dependency_overrides.pop(require_login_web, None)
    app.dependency_overrides.pop(require_login_api, None)


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
