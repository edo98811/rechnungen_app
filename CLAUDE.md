# CLAUDE.md

## Project

Receipt Scanner — extracts line items from photographed German supermarket
receipts (Rechnungen) into structured data, exportable as Excel. Single
user today, SQLite-backed persistence.

## Stack

- Backend: FastAPI (Python 3.12), single container
- Frontend: Jinja2 server-rendered templates
- Extraction: Gemini API vision (`generate_content` + Pydantic
  `response_schema`), `gemini-flash-latest`
- Excel export: openpyxl
- Dev loop: edit on host, run via `docker compose` (`uvicorn --reload`
  with a live volume mount, no devcontainer). `Dockerfile` has `dev`
  (pytest/httpx/pyright) and `production` (lean) stages; compose builds
  `target: dev`. Tests run via `docker compose run --rm backend pytest`.

## Next steps

- Authentication — done: single user via `.env` credentials
  (`app/auth.py`), structured so a users table is a drop-in swap later
  for real multi-user support.
- Persistence — done: `session_store.py` is now SQLite-backed (see file
  reference below) so receipts survive restarts and are no longer
  per-process.
- Delete receipts — needs planning before implementation. Add a "Delete
  selected" button to the dashboard (`app/templates/receipts_list.html`
  + `app/static/app.js`) alongside "Download selected", plus a delete
  endpoint (single vs. bulk shape TBD) and a new `delete_receipt`
  function in `app/services/session_store.py` (doesn't exist yet — only
  `save_receipt`/`get_receipt`/`list_receipts` exist today). Open
  questions: confirmation dialog before deleting, how the dashboard's
  `allReceipts`/`selectedIds` update after a delete (local removal vs.
  `refreshList()`), and hard-delete vs. soft-delete (a `deleted_at`
  column) for recoverability.

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
    receipts_list.html
  static/
    styles.css
    app.js
```

## File reference

- `pyproject.toml` — package `receipt-scanner`, Python >=3.12. Deps:
  fastapi, uvicorn[standard], jinja2, python-multipart, google-genai,
  openpyxl, pydantic-settings.
- `Dockerfile` — `python:3.12-slim` multi-stage: `base` (copies
  `pyproject.toml` + `app/`), `dev` (`pip install -e .[dev]`, used by
  compose), `production` (`pip install .`, runs `uvicorn app.main:app` on
  `0.0.0.0:8000`, no `--reload` — this is the deployed image).
- `docker-compose.yml` — one `backend` service, builds `target: dev`,
  publishes `8000:8000`, loads `.env`, bind-mounts the repo root,
  overrides the command to add `--reload` for local dev.
- `.env` / `.env.example` — secrets (`GEMINI_API_KEY`, `AUTH_USERNAME`,
  `AUTH_PASSWORD_HASH`, `SESSION_SECRET_KEY`) / committed template.
- `app/main.py` — FastAPI entrypoint. Mounts `/static`, includes
  `api_router` under `/api` and `web_router` unprefixed. `GET /health`.
- `app/config.py` — `Settings(BaseSettings)` from pydantic-settings,
  reads `.env`. Module-level singleton `settings`. Includes
  `database_path` (default `data/receipts.db`, env override
  `DATABASE_PATH`) for the SQLite store.
- `app/api/receipts.py` — JSON API router. `GET /receipts` (real data via
  `session_store.list_receipts`, as `[{"id", "receipt"}, ...]`),
  `POST /receipts/upload` (extract + store, returns id + receipt),
  `GET /receipts/{id}/export` (returns `.xlsx` bytes for one receipt),
  `POST /receipts/preview` (JSON body: array of receipt ids; loads each
  via `get_receipt`, skipping unknown ids; returns
  `{"rows": [...], "grand_total": ...}` via `compute_receipt_rows`, for
  the dashboard's live preview panel).
- `app/web/routes.py` — Jinja2 HTML router. `GET /` renders the dashboard
  shell (`receipts_list.html`, static — no receipt data passed in, JS
  fetches it). `POST /receipts/export` (form field `receipt_ids`, one or
  more ids; loads each via `get_receipt`, skipping unknown ids; 400 if
  none resolve; otherwise returns a combined `.xlsx` via
  `combine_receipts_to_excel`) for the "download selected" button.
- `app/services/extraction.py` — `extract_receipt(image_bytes, media_type)
  -> Receipt`, the Gemini vision extraction call.
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
- `app/templates/receipts_list.html` — dashboard shell (post-login `GET /`):
  static markup only, no Jinja loop over receipt data. Receipt table
  (`#receipt-rows` tbody, checkbox/date/shop columns) wrapped in the
  `#export-form` `<form action="/receipts/export" method="post">` so
  "download selected" works via plain browser form submission; reload
  button, upload file input + status span, "N selected" counter, and the
  `#preview-panel` container — all populated/driven by `app.js`.
- `app/static/styles.css` — minimal reset styling; also carries the
  dashboard's toolbar/upload-status/preview-panel styles.
- `app/static/app.js` — vanilla JS (no libraries/build step) driving the
  dashboard: `refreshList()` (GET `/api/receipts` → `renderList`),
  `uploadReceipt()` (POST `/api/receipts/upload`, updates `#upload-status`,
  then reloads the list), checkbox change handlers maintaining the
  `selectedIds` Set + `#selected-count`, and a debounced `updatePreview()`
  (POST `/api/receipts/preview` with the selected ids, renders the
  returned rows/grand_total into `#preview-panel`).

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
  the Gemini client (`app.services.extraction.client.models.generate_content`)
  — never calls the real Gemini API. Covers the success path and the
  no-text-returned error path.
- `app/auth.py` — `tests/test_auth.py`. Direct unit tests against
  `authenticate()`'s branches (correct/wrong password, wrong username, empty
  hash guard) and a session login/logout roundtrip against a bare fake
  request object — no HTTP layer needed for these.
- `app/api/receipts.py` — `tests/api/test_receipts.py`. `TestClient` against
  the real FastAPI app, auth bypassed via dependency override. Mocks
  `app.api.receipts.extract_receipt` for the upload test; saves fixture
  receipts straight via `session_store.save_receipt` for the export/list/
  preview tests (skips re-mocking extraction). Covers upload success,
  unsupported media type rejection, export of an unknown/known id
  (including reopening the response body with `openpyxl` to confirm it's a
  valid `.xlsx`), `GET /receipts` returning real saved receipts, and
  `POST /receipts/preview` returning rows/grand_total matching
  `compute_receipt_rows` directly (plus that unknown ids in the request are
  skipped rather than erroring).
- `app/web/routes.py` — `tests/web/test_routes.py`. Same `TestClient`
  approach, auth bypassed. Covers the dashboard shell rendering at `GET /`
  (light assertion — the reload button's id — rather than exact HTML
  matching, to avoid breaking on cosmetic template changes) and
  `POST /receipts/export`: a valid combined `.xlsx` containing only the
  selected receipts' rows (reopened with `openpyxl`), and a 400 when no
  receipt ids are selected.
