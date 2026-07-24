# Receipt Scanner

A single-user web app that turns photographed German supermarket receipts
into structured, exportable data. Take a photo of a receipt, upload it, and
the app extracts the store, date, and every line item (name, quantity,
price) into a database — then lets you browse, preview, combine, export to
Excel, or delete what's stored.

## The stack, in plain terms

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python), running
  in a single Docker container.
- **Frontend**: server-rendered HTML (Jinja2 templates) for the page
  shell, plus a small amount of hand-written vanilla JavaScript for the
  parts that need to feel live (list refresh, upload feedback, preview) —
  no React/Vue, no build step, no npm.
- **Receipt reading**: Google's Gemini API. A photo goes in, a
  structured JSON object (store, date, items, totals) comes out — the
  model does both the OCR *and* the structuring in one call.
- **Storage**: SQLite, a single file on disk. No separate database server.
- **Excel export**: [openpyxl](https://openpyxl.readthedocs.io/), builds
  `.xlsx` files in memory.
- **Auth**: a single hard-coded user (you), with a password hash stored
  in an environment file — no signup flow, no user database (yet).

## How it actually works, end to end

1. **You log in.** A plain username/password form checks your
   credentials against a password hash stored in `.env` (never your
   plaintext password). On success, the server hands your browser a
   signed cookie — that cookie is what keeps you logged in; there's no
   session data stored server-side beyond that.

2. **You land on the dashboard.** This is the app's home page — a list
   of every receipt you've uploaded, each row showing its date and shop
   name with a checkbox. The list isn't baked into the page when it
   loads; a small script fetches it live from the server right after the
   page appears, and can re-fetch it on demand (the "Reload" button).

3. **You upload a receipt.** Click "Upload," pick a photo. The browser
   sends it to the server, which sends it on to Gemini with a prompt
   asking it to extract the receipt's contents into a specific shape
   (store name, date, line items with quantities and prices, subtotal,
   tax, total). Gemini's response is validated against that exact shape
   — if it doesn't match, the upload fails loudly rather than silently
   storing garbage. If Gemini can't find a date on the receipt, today's
   date is used instead of leaving it blank or nonsensical. The
   extracted receipt is then saved to the SQLite database, and you see a
   success indicator as soon as that finishes — no page reload.

4. **You select receipts.** Checking boxes in the list doesn't talk to
   the server — the selection lives entirely in the browser (in a bit of
   JavaScript state) until you actually do something with it. As you
   check/uncheck boxes, a live preview panel below the list updates
   (after a brief pause, so it's not re-fetching on every single click)
   showing exactly what an export of your current selection would
   contain — every line item across all selected receipts, in one flat
   table.

5. **You export or delete.** "Download selected" builds a combined Excel
   file from whatever's checked and downloads it — one row per item
   across all selected receipts, tagged with which store/date/receipt it
   came from. "Delete selected" asks you to confirm, then permanently
   removes the selected receipts (and their line items) from the
   database — there's no undo.

## Where the critical logic actually lives

If you're trying to understand or change how something works, these are
the load-bearing files:

- **`app/services/extraction.py`** — the entire "turn a photo into
  structured data" step. This is where the Gemini API call happens, what
  prompt it's given, and how a malformed/missing response is handled
  (including the today's-date fallback). If receipt extraction is ever
  wrong or needs tuning, this is the file to look at.

- **`app/services/session_store.py`** — the entire database layer. Despite
  the name (a holdover from before persistence existed), this is not a
  session store — it's the SQLite access layer: saving, reading, listing,
  and deleting receipts. It also owns the database schema and any schema
  migrations. There's no ORM here — it's raw SQL, deliberately, because the
  schema is small and simple enough that an ORM would add a dependency
  without removing any code.

- **`app/services/excel_export.py`** — turns stored receipts into `.xlsx`
  bytes. There's one shared row-building function used by both the
  single-receipt export and the multi-receipt combined export, so they can
  never drift apart from each other.

- **`app/auth.py`** — the entire authentication story: password hashing
  and verification, session cookie handling, and the two guards
  (`require_login_web`, `require_login_api`) that every other route in the
  app depends on to stay protected. If you ever need to move from a single
  hard-coded user to real multi-user accounts, this file — specifically the
  `authenticate()` function — is the one seam designed to make that swap
  without touching anything else.

- **`app/api/receipts.py`** and **`app/web/routes.py`** — the two route
  files. `api/receipts.py` is the JSON API (what the page's JavaScript
  talks to); `web/routes.py` is the one HTML page the app serves (the
  dashboard itself, plus the file-download export route, since downloads
  need to be regular browser navigations, not JavaScript fetches).

- **`app/static/app.js`** — everything that happens in the browser without
  a page reload: fetching and re-rendering the receipt list, the live
  preview, upload progress feedback, and delete confirmation. This is
  plain JavaScript with no framework, so the whole interactive behavior of
  the dashboard is readable top-to-bottom in one file.

- **`app/models/receipt.py`** — the shape of a receipt, as a couple of
  small data classes. `Receipt` is also, not coincidentally, the exact
  schema handed to Gemini to constrain what it returns.

## What's deliberately *not* here yet

- **Multiple users.** The app is single-user by design right now, but
  `app/auth.py` and the database schema (`receipts.user_id`, currently
  always `"default"`) are both already shaped so that adding real
  multi-user accounts later is additive, not a rewrite.
- **Undo/soft-delete.** Deleting a receipt is permanent.
- **Filtering the receipt list.** Not built yet, but the dashboard's
  JavaScript is structured (a clear separation between "all the data,"
  "what's selected," and "what's currently drawn on screen") specifically
  so filtering can be added later without reworking how selection or
  rendering work.

## Running it

```
docker compose up
```

The app talks to Gemini and needs real credentials in `.env` (copy
`.env.example` and fill it in — `GEMINI_API_KEY`, plus `AUTH_USERNAME`/
`AUTH_PASSWORD_HASH`/`SESSION_SECRET_KEY` for login, with generation
instructions in the file's comments). Tests run via
`docker compose run --rm backend pytest`.
