# Authentication — how it works today

Single-user system. Two mechanisms exist side by side, checked in order
by the route guards: a session cookie for the browser dashboard, and a
static bearer token for non-browser clients (see
[`flutter_client.md`](flutter_client.md) for the token side from a
client's perspective). Both are backed by plain values in `.env`, not a
database — see "Multi-user seam" below for what's deliberately
provisional about that.

## 1. Session-cookie login (browser flow)

- `SessionMiddleware` is registered in `app/main.py`: signed cookie
  named `session`, `same_site="lax"`, secret key from
  `settings.session_secret_key`. Startup raises hard if that key isn't
  set — the app refuses to run without it.
- `GET /login` / `POST /login` live in `app/web/auth_routes.py` (not
  `app/web/routes.py`, which only holds routes that already require a
  logged-in session).
  - `GET /login` — if already authenticated, 303-redirects to
    `next` (or `/`); otherwise renders `login.html`.
  - `POST /login` — reads `username`, `password`, `next` form fields
    and calls `authenticate()`.
  - On success: `login_user()` sets `request.session["auth_user"] =
    username`, then 303-redirects to `next`, sanitized by
    `_safe_next()` to block `//`-style open redirects.
  - On failure: re-renders `login.html` with an error message and
    **HTTP 401** — not a redirect.
  - `POST /logout` pops `auth_user` from the session and redirects to
    `/login`.
- `is_authenticated(request)` (`app/auth.py`) just checks
  `"auth_user" in request.session`.
- `authenticate(username, password)` (`app/auth.py`):
  timing-safe username compare via `hmac.compare_digest`, plus
  `pbkdf2_sha256.verify(password, settings.auth_password_hash)`. If no
  hash is configured (`auth_password_hash == ""`), it always returns
  `False` — a deliberate guard, since passlib's `verify()` raises on an
  empty/invalid hash rather than just failing the check.

## 2. Bearer API token (non-browser clients)

- `_has_valid_api_token(request)` (`app/auth.py`) checks
  `Authorization: Bearer <token>` against `settings.api_token` via
  `hmac.compare_digest`.
- `settings.api_token` is empty by default, which disables this path
  entirely until a value is set in `.env` — there's no way to
  accidentally expose an API-token bypass on a fresh install.
- Only wired into API routes (via `require_login_api`), not web routes.

## Route guards

- `require_login_web` — used on HTML pages. 303-redirects to
  `/login?next=<path>` if not authenticated.
- `require_login_api` — used on JSON API routes. Accepts *either* a
  valid session cookie *or* a valid bearer token; 401s otherwise.

## Multi-user seam

Per `CLAUDE.md`, `authenticate()` is deliberately the one seam a future
multi-user version would swap for a real `users`-table lookup —
everything else (session helpers, FastAPI dependency guards) is
storage-agnostic and wouldn't need to change. Today:

- Credentials (`AUTH_USERNAME`, `AUTH_PASSWORD_HASH`) and the API token
  (`API_TOKEN`) are single static values from `.env`, not per-user rows.
- `receipts.user_id` is already threaded through every query in
  `session_store.py`, but hardcoded to `"default"` everywhere it's
  used.
- The API token is shared and non-revocable per-user — rotating
  `API_TOKEN` invalidates it for every client at once.

## Test coverage gap

`tests/test_auth.py` unit-tests `authenticate()`'s branches directly,
does a bare session login/logout roundtrip against a fake request
object, and checks `require_login_api`'s bearer-token branch — plus two
`TestClient`-level checks that `GET /api/receipts` enforces auth (401
with no header, 200 with a correct bearer token). There is currently no
HTTP-level (`TestClient`) test of the `/login` or `/logout` routes
themselves.
