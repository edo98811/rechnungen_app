from passlib.hash import pbkdf2_sha256  # type: ignore[attr-defined]

from app.auth import authenticate, is_authenticated, login_user, logout_user
from app.config import settings


def test_authenticate_correct_credentials_returns_true(monkeypatch):
    monkeypatch.setattr(settings, "auth_username", "alice")
    monkeypatch.setattr(
        settings, "auth_password_hash", pbkdf2_sha256.hash("correct-horse")
    )

    assert authenticate("alice", "correct-horse") is True


def test_authenticate_wrong_password_returns_false(monkeypatch):
    monkeypatch.setattr(settings, "auth_username", "alice")
    monkeypatch.setattr(
        settings, "auth_password_hash", pbkdf2_sha256.hash("correct-horse")
    )

    assert authenticate("alice", "wrong-password") is False


def test_authenticate_wrong_username_returns_false(monkeypatch):
    monkeypatch.setattr(settings, "auth_username", "alice")
    monkeypatch.setattr(
        settings, "auth_password_hash", pbkdf2_sha256.hash("correct-horse")
    )

    assert authenticate("bob", "correct-horse") is False


def test_authenticate_empty_hash_returns_false(monkeypatch):
    monkeypatch.setattr(settings, "auth_username", "alice")
    monkeypatch.setattr(settings, "auth_password_hash", "")

    assert authenticate("alice", "correct-horse") is False


def test_login_logout_session_roundtrip():
    class FakeRequest:
        session: dict = {}

    fake_request = FakeRequest()

    login_user(fake_request, "alice")  # type: ignore[arg-type]
    assert is_authenticated(fake_request) is True  # type: ignore[arg-type]

    logout_user(fake_request)  # type: ignore[arg-type]
    assert is_authenticated(fake_request) is False  # type: ignore[arg-type]
