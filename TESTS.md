# Test Suite

## `tests/test_auth.py`

| endpoint or function(s) tested | Scenario | Expected result |
|---|---|---|
| `authenticate` | Correct username and password | Returns `True` |
| `authenticate` | Correct username, wrong password | Returns `False` |
| `authenticate` | Wrong username | Returns `False` |
| `authenticate` | `auth_password_hash` is empty (unconfigured) | Returns `False` |
| `require_login_api` | Request carries a valid `Authorization: Bearer <API_TOKEN>` header | No exception raised (request allowed through) |
| `require_login_api` | Request carries a bearer token that doesn't match the configured `api_token` | Raises `HTTPException` with `status_code == 401` |
| `require_login_api` | `api_token` is unconfigured (empty), any bearer token sent | Raises `HTTPException` with `status_code == 401` |
| `require_login_api` | No bearer token, but a valid session (`auth_user` set) | No exception raised (session auth accepted) |
| `GET /api/receipts` | Request sent with no `Authorization` header, `api_token` configured | Response status `401` |
| `GET /api/receipts` | Request sent with correct bearer token, `api_token` configured | Response status `200` |
| `login_user`, `is_authenticated`, `logout_user` | Login then logout roundtrip on a fake request/session object | `is_authenticated` is `True` after login, `False` after logout |

## `tests/services/test_session_store.py`

| endpoint or function(s) tested | Scenario | Expected result |
|---|---|---|
| `session_store.save_receipt`, `get_receipt` | Save a receipt, then fetch it by id | Returned `StoredReceipt` matches all saved fields (store name, date, `user_id="default"`, items, subtotal, tax, total) |
| `session_store.get_receipt` | Lookup with an id that was never saved | Returns `None` |
| `session_store.list_receipts` | Three receipts saved in sequence, no filters | Returned list preserves insertion order (by id and by store name) |
| `session_store.list_receipts` | Three receipts across different months, filtered with both `date_from` and `date_to` | Only the receipt inside the range is returned; receipts before/after are excluded |
| `session_store.list_receipts` | `date_from` and `date_to` set to the same date as the receipt's date | Receipt is included (boundaries are inclusive) |
| `session_store.list_receipts` | Only `date_from` provided (no `date_to`) | Only receipts on/after that date are returned |
| `session_store.delete_receipt` | Delete a receipt that exists | Returns `True`; `get_receipt` afterward returns `None`; no rows remain in `receipt_items` for that receipt id (checked via direct SQL) |
| `session_store.delete_receipt` | Delete an id that was never saved | Returns `False` |
| `session_store._get_connection` (migrations) | Open a connection, close it, then reopen a fresh connection to the same DB file | `PRAGMA user_version` equals the number of defined migrations; the `receipts` table is still queryable |
| `session_store.save_receipt`, `get_receipt` | Save via one connection, then fetch via a freshly-opened connection (no shared in-memory state) | Data is still readable — persistence lives in the file, not a cached connection |

## `tests/services/test_excel_export.py`

| endpoint or function(s) tested | Scenario | Expected result |
|---|---|---|
| `receipt_to_excel` | Single receipt with 2 line items | Generated `.xlsx` header row matches `HEADERS`; each data row matches the item's name/total/quantity/unit price plus the receipt's user_id/date/store; sheet has no grand-total row (ends right after the last item row) |
| `compute_receipt_rows` | Single receipt passed in | Returns one row per item, in `(name, total_price, quantity, unit_price, user_id, date, store_name)` order; grand total equals the receipt's `total` |
| `compute_receipt_rows` | Two receipts (different users/stores/dates) passed in | Returns 4 rows total, receipt A's rows first then receipt B's; grand total is the sum of both receipts' totals |
| `combine_receipts_to_excel` | Three receipts exist, only two ids passed in | Generated workbook contains rows only for the two selected receipts' stores; the third (unselected) receipt's store name does not appear; row count is exactly 1 header + 4 item rows |

## `tests/services/test_extraction.py`

| endpoint or function(s) tested | Scenario | Expected result |
|---|---|---|
| `extract_receipt` | Gemini call succeeds and returns valid receipt JSON text | Returns a `Receipt` equal to the expected fixture |
| `extract_receipt` | Gemini response has `text=None` | Raises `ValueError` matching "did not return a parsed receipt" |
| `extract_receipt` | Gemini returns a receipt whose `date` field isn't a valid date (`"N/A"`) | Returned receipt's `date` is silently replaced with today's date (ISO format) |
| `extract_receipt` | `GEMINI_API_KEY` is unset (empty) | Raises `ValueError` matching "GEMINI_API_KEY is not configured" |
| `extract_receipt` | Gemini's client raises `google.genai.errors.APIError` (e.g. 503 "high demand") | Raises `ValueError` (specifically `GeminiOutageError`) matching "Gemini API error: high demand" |

## `tests/api/test_receipts.py`

Auth is bypassed for all tests in this file via the `bypass_auth` fixture (applied automatically through `tests/api/conftest.py`).

| endpoint or function(s) tested | Scenario | Expected result |
|---|---|---|
| `GET /api/receipts` | Two receipts saved directly via `session_store.save_receipt` | Response `200`; returned ids match both saved receipts; each entry's `store_name` matches |
| `GET /api/receipts` | Two receipts saved with different dates, request filtered with `date_from`/`date_to` | Response `200`; only the in-range receipt's id is returned |
| `POST /api/receipts/preview` | Two saved receipt ids submitted | Response `200`; `rows`/`grand_total` match `compute_receipt_rows` computed directly from the stored receipts; first row's product name matches |
| `POST /api/receipts/preview` | One real id + one nonexistent id submitted | Response `200`; only one row returned (unknown id silently skipped) |
| `POST /api/receipts/delete` | Two receipts saved, request includes one real id + one nonexistent id | Response `200`; body reports only the real id as `deleted`; that receipt is gone from the store, the second (unselected) receipt still exists |
| `POST /api/receipts/upload` | `extract_receipt` mocked to succeed, valid JPEG file uploaded | Response `200`; body contains an `id` and a `receipt` whose `store_name`/`total` match the mocked extraction result |
| `POST /api/receipts/upload` | File uploaded with `content_type="text/plain"` (unsupported) | Response `400` |
| `POST /api/receipts/upload` | `extract_receipt` raises `GeminiOutageError` | Response `503`; body's `detail.error` is `"gemini outage"` |
| `POST /api/receipts/upload` | `extract_receipt` raises `NoReceiptTextError` | Response `503`; body's `detail.error` is `"no text"` |
| `POST /api/receipts/upload` | `extract_receipt` raises a `pydantic.ValidationError` (schema mismatch) | Response `503`; body's `detail.error` is `"schema mismatch"` |
| `GET /api/receipts/{id}/export` | Id does not exist in the store | Response `404` |
| `GET /api/receipts/{id}/export` | Id exists (receipt saved beforehand) | Response `200`; `content-type` is the xlsx MIME type; response body reopens successfully as a valid `.xlsx` workbook |

## `tests/web/test_routes.py`

Auth is bypassed for all tests in this file via the `bypass_auth` fixture (applied automatically through `tests/web/conftest.py`).

| endpoint or function(s) tested | Scenario | Expected result |
|---|---|---|
| `GET /` | Dashboard shell requested | Response `200`; HTML contains the `reload-btn` element id |
| `POST /receipts/export` | Two receipts saved, only one id submitted in the form | Response `200`; xlsx `content-type`; the generated workbook's line-item rows include only the selected receipt's item, not the unselected duplicate's |
| `POST /receipts/export` | No `receipt_ids` in the form data | Response `400` |

## Skipped

None — every test file found under `tests/` (`test_auth.py`, `tests/services/*.py`, `tests/api/test_receipts.py`, `tests/web/test_routes.py`) was read and cataloged. `tests/conftest.py`, `tests/api/conftest.py`, and `tests/web/conftest.py` contain only fixtures (no test cases) and are referenced above where their fixtures affect test behavior (`bypass_auth`, `sample_receipt`, `_isolated_session_store`).
