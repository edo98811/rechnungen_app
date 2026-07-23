"""Single-user auth: session-cookie login backed by credentials in .env.

`authenticate()` is the one seam a future multi-user version would swap
for a DB lookup — everything else here (session helpers, FastAPI
dependencies) is storage-agnostic and would not need to change.
"""

import getpass
import hmac

from fastapi import HTTPException, Request
from passlib.hash import pbkdf2_sha256  # type: ignore[attr-defined]

from app.config import settings


def authenticate(username: str, password: str) -> bool:
    if not settings.auth_password_hash:
        return False  # "" default isn't a valid hash; verify() would raise on it
    return (
        hmac.compare_digest(username, settings.auth_username)
        and pbkdf2_sha256.verify(password, settings.auth_password_hash)
    )


def login_user(request: Request, username: str) -> None:
    request.session["auth_user"] = username


def logout_user(request: Request) -> None:
    request.session.pop("auth_user", None)


def is_authenticated(request: Request) -> bool:
    return "auth_user" in request.session


def require_login_web(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(
            status_code=303,
            headers={"Location": f"/login?next={request.url.path}"},
        )


def require_login_api(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")


if __name__ == "__main__":
    password = getpass.getpass("Password to hash: ")
    print(pbkdf2_sha256.hash(password))
