from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.receipts import router as api_router
from app.config import settings
from app.web.auth_routes import router as auth_router
from app.web.routes import router as web_router

app = FastAPI(title="Receipt Scanner")

if not settings.session_secret_key:
    raise RuntimeError("SESSION_SECRET_KEY must be set (see .env.example)")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    session_cookie="session",
    same_site="lax",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(api_router, prefix="/api")
app.include_router(auth_router)
app.include_router(web_router)


@app.get("/health")
def health():
    return {"status": "ok"}
