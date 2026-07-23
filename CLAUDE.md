# CLAUDE.md

## Project

Receipt Scanner — extracts line items from photographed German supermarket
receipts (Rechnungen) into structured data, exportable as Excel. Single user
today. Per-browser signed-cookie identity + history is the next planned
feature; full user accounts (login/password) are explicitly deferred until
there's a real need for them.

## Stack

- Backend: FastAPI (Python 3.12), single container for now
- Frontend: Jinja2 server-rendered templates. May split into a separate
  SvelteKit frontend + container later — the `app/api/` vs `app/web/` split
  exists specifically to make that split easy (see Architecture below)
- Extraction: Claude API vision (`messages.parse` + Pydantic `output_format`),
  `claude-opus-4-8` by default
- Excel export: openpyxl
- Hosting target: AWS Lightsail Containers (not yet deployed)
- Dev loop: devcontainer + docker-compose, `uvicorn --reload` +
  `./app:/app/app` volume mount for live reload on save

## Architecture

- `app/api/` — JSON endpoints. What a future separate frontend would call.
- `app/web/` — Jinja2-rendered HTML routes, plus `templates/` and `static/`.
  Disposable: gets deleted if/when the frontend splits into its own
  container; everything else stays as-is.
- `app/services/` — business logic (Claude extraction, Excel export,
  storage). Never touches HTTP or templates directly.
- `app/models/` — Pydantic data shapes only, no logic.

## File Reference

Everything that exists right now, so this doesn't need to be rediscovered by
reading files. Update this section whenever a file's purpose or exports
change materially — stale entries here are worse than no entry.

### Root

- `pyproject.toml` — package `receipt-scanner`, Python >=3.12. Deps: fastapi,
  uvicorn[standard], jinja2, python-multipart, anthropic, openpyxl,
  pydantic-settings. setuptools backend, `packages.find include = ["app*"]`.
- `Dockerfile` — `python:3.12-slim`, installs from `pyproject.toml`, copies
  `app/`, runs `uvicorn app.main:app` on `0.0.0.0:8000` with no `--reload`
  (this is the production command).
- `docker-compose.yml` — one `backend` service, builds from `Dockerfile`,
  publishes `8000:8000`, loads `.env`, bind-mounts the whole repo root
  (`.:/app`, not just `app/`) so `.git`, `.claude/`, etc. are visible and
  live-editable inside the devcontainer too, and overrides the container
  command to add `--reload` for local dev only.
- `.env` — real secrets, gitignored. `.env.example` — template, committed.
  Currently just `ANTHROPIC_API_KEY`.
- `.gitignore` — standard Python ignores + `.env` + `uploads/` + `.claude`
  (only affects untracked files under it — `.claude/settings.json` and
  `.claude/settings.local.json` stay tracked as before) + `CHANGES.md`
  (local session notes, not shared history).
- `.devcontainer/devcontainer.json` — reopens VSCode inside the `backend`
  compose service, forwards port 8000, `node` feature only. Claude Code is
  not used from inside this container — develop with it from the host
  instead, where it isn't running as root and needs no special permission
  workarounds; the devcontainer is just for running/debugging the app.
- `.claude/settings.json` — allowlists `docker compose *`, `docker *`,
  `cat *`, `ls *` for this project (no prompts for those).

### `app/main.py`

FastAPI app entrypoint. Mounts `/static`, includes `api_router` under
`/api` and `web_router` unprefixed. Defines `GET /health` →
`{"status": "ok"}`.

### `app/config.py`

`Settings(BaseSettings)` from pydantic-settings, reads `.env`. One field so
far: `anthropic_api_key: str = ""`. Module-level singleton: `settings`.

### `app/api/receipts.py`

JSON API router (`tags=["receipts"]`). `GET /receipts` → stub returning
`[]`. `POST /receipts/upload` — takes a multipart `UploadFile`, validates
`content_type` against `SupportedMediaType` (400 if unsupported), calls
`extract_receipt`, stores the result via `session_store.save_receipt`,
returns `{"id": ..., "receipt": ...}`. `GET /receipts/{receipt_id}/export`
— looks up the receipt via `session_store.get_receipt` (404 if missing),
returns `receipt_to_excel(receipt)` bytes as an `.xlsx` attachment
(`Content-Disposition: attachment`).

### `app/web/routes.py`

Jinja2 HTML router. `GET /` → renders `index.html` (upload form). `POST
/upload` — same extraction + `session_store.save_receipt` flow as the API
route (calls the services directly, not the API over HTTP), renders
`result.html` with the receipt and its `receipt_id`. Uses
`Jinja2Templates(directory="app/templates")`.

### `app/services/session_store.py`

In-memory-only receipt store: `_receipts: dict[str, Receipt]` at module
scope. `save_receipt(receipt) -> str` generates a `uuid4().hex` id, stores
the receipt, returns the id. `get_receipt(receipt_id) -> Receipt | None`.
No persistence — cleared on process restart, not shared across workers.
This is the deliberate stand-in for real per-browser session storage until
the signed-cookie identity work lands: the id is simply handed back to the
client (embedded in the `result.html` download link) rather than tied to
any cookie/session concept yet.

### `app/templates/base.html`

Base layout: `<head>` with title + link to `/static/styles.css`, and a
`{% block content %}` for child templates to fill.

### `app/templates/index.html`

Extends `base.html`. Upload form: `<form action="/upload" method="post"
enctype="multipart/form-data">` with a file input restricted to the
supported image MIME types via `accept`.

### `app/templates/result.html`

Extends `base.html`. Renders the extracted `Receipt` (store, date, an
items table, subtotal/tax/total) plus a "Download Excel" link to
`/api/receipts/{receipt_id}/export` and a link back to `/`.

### `app/static/styles.css`

Minimal reset (font, max-width, margin). Nothing else styled yet.

### `app/services/extraction.py`

The core Claude vision extraction call. Module-level
`client = anthropic.Anthropic(api_key=settings.anthropic_api_key)`.
`SupportedMediaType = Literal["image/jpeg", "image/png", "image/gif", "image/webp"]`.
`extract_receipt(image_bytes: bytes, media_type: SupportedMediaType) -> Receipt`:
base64-encodes the image, calls `client.messages.parse(model="claude-opus-4-8", output_format=Receipt, ...)`
with typed `ImageBlockParam`/`TextBlockParam`/`MessageParam` content blocks
(see typing notes below), raises `ValueError` if `parsed_output` is `None`.
Prompt is tuned for German number/date formats. Pyright-clean.
**Not yet verified against a real receipt photo + real API key** — only
import/type-checked so far.

### `app/services/excel_export.py`

`receipt_to_excel(receipt: Receipt) -> bytes` — builds one xlsx sheet via
openpyxl: store/date header rows, bold column headers (Item/Quantity/Unit
Price/Total Price), one row per item with currency-formatted price cells,
then Subtotal/Tax/Total rows (value always in column D, so it lines up with
the item totals above). Auto-sized column widths via `get_column_letter`
(not `cell.column_letter` — that fails pyright because `sheet.columns`
yields `Cell | MergedCell` and only `Cell` has that attribute). Writes to
an in-memory `BytesIO`, returns raw bytes — no filesystem dependency.
Pyright-clean, verified end-to-end against a fixture `Receipt` (built and
re-opened with `openpyxl.load_workbook`, contents checked cell-by-cell).

### `app/models/receipt.py`

Pydantic shapes only, no logic. `ReceiptItem(name, quantity, unit_price,
total_price)`. `Receipt(store_name, date [ISO 8601 string], items: list[ReceiptItem],
subtotal, tax_amount, total)`.

### Everything else

All `__init__.py` files (`app/`, `app/api/`, `app/web/`, `app/services/`,
`app/models/`) are empty package markers — nothing to document.

## Status

- [x] Scaffold: FastAPI + Jinja2, single container, verified booting
      (`/health`, `/`)
- [x] `services/extraction.py` — Claude vision extraction, typed and
      pyright-clean
- [x] `services/excel_export.py` — openpyxl export, typed, pyright-clean,
      verified against a fixture receipt
- [x] Upload route (api + web) — `POST /api/receipts/upload` and `POST
      /upload`, plus `GET /api/receipts/{id}/export` for the Excel
      download. Results held only in the in-memory
      `services/session_store.py` (see File Reference), not persisted.
      Pyright-clean; routing, 400 (bad media type), and 404 (unknown id)
      paths verified against a running container. `extract_receipt` itself
      still only verified with fixtures, not a real photo — see the
      `extraction.py` entry above.
- [ ] Persistence (SQLite via SQLModel) + per-browser signed-cookie
      identity + `services/storage.py` (saving the uploaded image) — all
      deferred together, not started. `storage.py` was scaffolded then
      deleted: no persistence yet means nothing to save the image *for*.
      `session_store.py`'s in-memory dict is the interim stand-in and will
      likely be replaced or backed by this once it lands.

## Anthropic SDK calls — typing

When building `messages` for `client.messages.create()` / `.parse()`, don't pass raw untyped dict literals for content blocks. A list mixing dict shapes (e.g. an image block and a text block) gets inferred by pyright as an overly broad type that doesn't structurally match `Iterable[MessageParam]`, causing errors in VSCode/Pylance.

Instead, annotate each content block with its SDK TypedDict (`anthropic.types.TextBlockParam`, `ImageBlockParam`, etc.) before putting it in the list, and annotate the final list as `list[MessageParam]`. See `app/services/extraction.py` for the pattern.

- `media_type` on image/document source blocks is a `Literal` of specific MIME strings (`"image/jpeg" | "image/png" | "image/gif" | "image/webp"`), not `str` — mirror that in any function signature that accepts a media type, so callers are forced to pass a valid value.
- `response.parsed_output` from `messages.parse()` is typed `T | None`. Check for `None` and raise inside the service function rather than widening the return type to `Optional` — callers should get a guaranteed non-None value, not have to null-check on every call site.

## openpyxl — typing

- `workbook.active` is typed `Worksheet | None` — `assert sheet is not None` right after getting it (a fresh `Workbook()` always has an active sheet in practice, pyright just can't know that).
- `sheet.columns` yields tuples of `Cell | MergedCell`, and `MergedCell` has no `.column_letter`. Don't read `.column_letter` off a cell from `sheet.columns`/`sheet.rows` iteration. Use `enumerate(sheet.columns, start=1)` and `openpyxl.utils.get_column_letter(index)` instead.

## Verifying a change (the standard we hold each service to)

Don't declare a service function done just because it imports cleanly.
Before checking a box in Status:
1. `pyright <file>` — install via `pip install pyright` in-container if not
   present (needs `libatomic1` too — `apt-get install -y libatomic1` first).
2. Actually call the function with realistic fixture data inside the
   container (`docker compose run --rm backend python -c "..."`) and inspect
   the real output, not just that it didn't throw.
3. For `extraction.py` specifically, pyright + fixture calls aren't enough —
   it needs a real `ANTHROPIC_API_KEY` and a real receipt photo to know if
   it's actually *correct*, not just wired correctly. Flag that distinction
   when reporting status.
