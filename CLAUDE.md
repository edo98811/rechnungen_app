# CLAUDE.md

## Project

Receipt Scanner — extracts line items from photographed German supermarket
receipts (Rechnungen) into structured data, exportable as Excel. Single
user today, in-memory storage only (no persistence yet).

## Stack

- Backend: FastAPI (Python 3.12), single container
- Frontend: Jinja2 server-rendered templates
- Extraction: Claude API vision (`messages.parse` + Pydantic `output_format`),
  `claude-opus-4-8`
- Excel export: openpyxl
- Dev loop: edit on host, run via `docker compose` (`uvicorn --reload`
  with a live volume mount, no devcontainer). `Dockerfile` has `dev`
  (pytest/httpx/pyright) and `production` (lean) stages; compose builds
  `target: dev`. Tests run via `docker compose run --rm backend pytest`.

## Next steps

- Authentication — start with a single user, but build the model so more
  users can be added later (not full self-service signup, just
  multi-user-capable from the start).
- Persistence — replace `session_store.py`'s in-memory dict with a SQLite
  database so receipts survive restarts and are no longer per-process.

## File structure

```
pyproject.toml
Dockerfile
docker-compose.yml
.env / .env.example
app/
  main.py
  config.py
  api/
    receipts.py
  web/
    routes.py
  services/
    extraction.py
    excel_export.py
    session_store.py
  models/
    receipt.py
  templates/
    base.html
    index.html
    result.html
  static/
    styles.css
```

## File reference

- `pyproject.toml` — package `receipt-scanner`, Python >=3.12. Deps:
  fastapi, uvicorn[standard], jinja2, python-multipart, anthropic,
  openpyxl, pydantic-settings.
- `Dockerfile` — `python:3.12-slim` multi-stage: `base` (copies
  `pyproject.toml` + `app/`), `dev` (`pip install -e .[dev]`, used by
  compose), `production` (`pip install .`, runs `uvicorn app.main:app` on
  `0.0.0.0:8000`, no `--reload` — this is the deployed image).
- `docker-compose.yml` — one `backend` service, builds `target: dev`,
  publishes `8000:8000`, loads `.env`, bind-mounts the repo root,
  overrides the command to add `--reload` for local dev.
- `.env` / `.env.example` — secrets (`ANTHROPIC_API_KEY`,
  `CLAUDE_CODE_OAUTH_TOKEN`) / committed template.
- `app/main.py` — FastAPI entrypoint. Mounts `/static`, includes
  `api_router` under `/api` and `web_router` unprefixed. `GET /health`.
- `app/config.py` — `Settings(BaseSettings)` from pydantic-settings,
  reads `.env`. Module-level singleton `settings`.
- `app/api/receipts.py` — JSON API router. `GET /receipts` (stub `[]`),
  `POST /receipts/upload` (extract + store, returns id + receipt),
  `GET /receipts/{id}/export` (returns `.xlsx` bytes).
- `app/web/routes.py` — Jinja2 HTML router. `GET /` renders the upload
  form, `POST /upload` runs the same extraction flow and renders the
  result page.
- `app/services/extraction.py` — `extract_receipt(image_bytes, media_type)
  -> Receipt`, the Claude vision extraction call.
- `app/services/excel_export.py` — `receipt_to_excel(receipt) -> bytes`,
  builds an xlsx workbook in memory via openpyxl.
- `app/services/session_store.py` — in-memory `dict[str, Receipt]` store,
  `save_receipt` / `get_receipt`. No persistence, not shared across
  workers.
- `app/models/receipt.py` — Pydantic shapes: `ReceiptItem`, `Receipt`.
- `app/templates/base.html` — base layout, `{% block content %}`.
- `app/templates/index.html` — upload form.
- `app/templates/result.html` — extracted receipt view + Excel download
  link.
- `app/static/styles.css` — minimal reset styling.
