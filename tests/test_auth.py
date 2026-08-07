from fastapi import HTTPException
from fastapi.testclient import TestClient
from passlib.hash import pbkdf2_sha256  # type: ignore[attr-defined]

from app.auth import authenticate, is_authenticated, login_user, logout_user, require_login_api
from app.config import settings
from app.main import app


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


class _FakeApiRequest:
    def __init__(self, headers: dict | None = None, session: dict | None = None):
        self.headers = headers or {}
        self.session = session if session is not None else {}


def test_require_login_api_accepts_valid_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret-token")

    request = _FakeApiRequest(headers={"Authorization": "Bearer secret-token"})

    require_login_api(request)  # type: ignore[arg-type]


def test_require_login_api_rejects_wrong_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret-token")

    request = _FakeApiRequest(headers={"Authorization": "Bearer wrong-token"})

    try:
        require_login_api(request)  # type: ignore[arg-type]
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401


def test_require_login_api_rejects_token_when_none_configured(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "")

    request = _FakeApiRequest(headers={"Authorization": "Bearer anything"})

    try:
        require_login_api(request)  # type: ignore[arg-type]
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401


def test_require_login_api_accepts_session_without_token(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret-token")

    request = _FakeApiRequest(session={"auth_user": "alice"})

    require_login_api(request)  # type: ignore[arg-type]


def test_api_endpoint_rejects_request_without_token(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret-token")
    client = TestClient(app)

    response = client.get("/api/receipts")

    assert response.status_code == 401


def test_api_endpoint_accepts_valid_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret-token")
    client = TestClient(app)

    response = client.get(
        "/api/receipts", headers={"Authorization": "Bearer secret-token"}
    )

    assert response.status_code == 200


def test_login_logout_session_roundtrip():
    class FakeRequest:
        session: dict = {}

    fake_request = FakeRequest()

    login_user(fake_request, "alice")  # type: ignore[arg-type]
    assert is_authenticated(fake_request) is True  # type: ignore[arg-type]

    logout_user(fake_request)  # type: ignore[arg-type]
    assert is_authenticated(fake_request) is False  # type: ignore[arg-type]
