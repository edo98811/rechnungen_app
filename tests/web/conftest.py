import pytest


@pytest.fixture(autouse=True)
def _auto_bypass_auth(bypass_auth):
    """Apply the shared auth bypass to every test under tests/web/."""
