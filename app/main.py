from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.receipts import router as api_router
from app.web.routes import router as web_router

app = FastAPI(title="Receipt Scanner")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(api_router, prefix="/api")
app.include_router(web_router)


@app.get("/health")
def health():
    return {"status": "ok"}
