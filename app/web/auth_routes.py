from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import authenticate, is_authenticated, login_user, logout_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _safe_next(next: str) -> str:
    if next.startswith("/") and not next.startswith("//"):
        return next
    return "/"


@router.get("/login")
def login_form(request: Request, next: str = "/"):
    if is_authenticated(request):
        return RedirectResponse(_safe_next(next), status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"next": _safe_next(next)}
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    safe_next = _safe_next(next)
    if authenticate(username, password):
        login_user(request, username)
        return RedirectResponse(safe_next, status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {"next": safe_next, "error": "Invalid username or password."},
        status_code=401,
    )


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/login", status_code=303)
