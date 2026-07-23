# CLAUDE.md

## Project

Receipt Scanner — extracts line items from photographed German supermarket
receipts (Rechnungen) into structured data, exportable as Excel. Single
user today, SQLite-backed persistence.

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
- Persistence — done: `session_store.py` is now SQLite-backed (see file
  reference below) so receipts survive restarts and are no longer
  per-process.

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
- `.env` / `.env.example` — secrets (`ANTHROPIC_API_KEY`, `AUTH_USERNAME`,
  `AUTH_PASSWORD_HASH`, `SESSION_SECRET_KEY`) / committed template.
- `app/main.py` — FastAPI entrypoint. Mounts `/static`, includes
  `api_router` under `/api` and `web_router` unprefixed. `GET /health`.
- `app/config.py` — `Settings(BaseSettings)` from pydantic-settings,
  reads `.env`. Module-level singleton `settings`. Includes
  `database_path` (default `data/receipts.db`, env override
  `DATABASE_PATH`) for the SQLite store.
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
- `app/services/session_store.py` — SQLite-backed store (raw stdlib
  `sqlite3`, no ORM) with two tables, `receipts` and `receipt_items`
  (one row per line item, so per-item queries stay plain SQL). Schema
  migrations are plain SQL scripts tracked via `PRAGMA user_version`
  (see `_MIGRATIONS`), not Alembic. `save_receipt` / `get_receipt` /
  `list_receipts` keep their existing call shapes; `get_receipt` and
  `list_receipts` now return `StoredReceipt` (tagged `user_id`,
  currently always `"default"` — no `users` table yet). Reads
  `settings.database_path` fresh on every call (no cached connection),
  creating the parent directory if needed.
- `app/models/receipt.py` — Pydantic shapes: `ReceiptItem`, `Receipt`.
- `app/templates/base.html` — base layout, `{% block content %}`.
- `app/templates/index.html` — upload form.
- `app/templates/result.html` — extracted receipt view + Excel download
  link.
- `app/static/styles.css` — minimal reset styling.

## Testing

Run via `docker compose run --rm backend pytest`. Route tests bypass auth
via FastAPI dependency overrides (see `tests/conftest.py`'s `bypass_auth`
fixture, applied automatically to everything under `tests/api/` and
`tests/web/` via their own nested `conftest.py` autouse fixtures) rather
than re-testing login itself — `tests/test_auth.py` covers login directly
and would break if auth were bypassed tree-wide, so `bypass_auth` is not
global-autouse.

- `app/services/session_store.py` — `tests/services/test_session_store.py`.
  Real SQLite file per test (`tmp_path`-backed, via `settings.database_path`
  monkeypatch). Covers save/get roundtrip, unknown-id lookup, insertion-order
  listing, migration idempotency, persistence across a fresh connection.
- `app/services/excel_export.py` — `tests/services/test_excel_export.py`.
  Builds fixture `StoredReceipt`s, reopens the generated `.xlsx` bytes with
  `openpyxl` to assert on actual cell contents. Covers single-receipt export,
  the pure row-computation function directly, and multi-receipt combining
  (including that unselected receipts are excluded).
- `app/services/extraction.py` — `tests/services/test_extraction.py`. Mocks
  the Anthropic client (`app.services.extraction.client.messages.parse`) —
  never calls the real Claude API. Covers the success path and the
  `None`-parsed-output error path.
- `app/auth.py` — `tests/test_auth.py`. Direct unit tests against
  `authenticate()`'s branches (correct/wrong password, wrong username, empty
  hash guard) and a session login/logout roundtrip against a bare fake
  request object — no HTTP layer needed for these.
- `app/api/receipts.py` — `tests/api/test_receipts.py`. `TestClient` against
  the real FastAPI app, auth bypassed via dependency override. Mocks
  `app.api.receipts.extract_receipt` for the upload test; saves a fixture
  receipt straight via `session_store.save_receipt` for the export tests
  (skips re-mocking extraction). Covers upload success, unsupported media
  type rejection, and export of an unknown/known id (including reopening
  the response body with `openpyxl` to confirm it's a valid `.xlsx`).
- `app/web/routes.py` — `tests/web/test_routes.py`. Same `TestClient`
  approach, auth bypassed. Covers the upload form rendering and the result
  page rendering real receipt data (mocking `app.web.routes.extract_receipt`)
  — assertions are light (status code + key content) rather than exact HTML
  matching, to avoid breaking on cosmetic template changes.
