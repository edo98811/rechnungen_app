let allReceipts = [];
const selectedIds = new Set();

let previewDebounceTimer = null;

/**
 * Rebuilds the `#receipt-rows` table body from scratch for the given
 * `receipts` array (each entry `{ id, receipt }`, as returned by
 * `GET /api/receipts`). For every entry, creates a row with a checkbox
 * (checked if `id` is already in `selectedIds`), a date cell, and a store
 * name cell. The checkbox's `change` handler adds/removes `id` from
 * `selectedIds` and then calls `updateSelectedCount()` and
 * `updatePreview()` to keep the counter and preview panel in sync.
 */
function renderList(receipts) {
  const tbody = document.getElementById("receipt-rows");
  tbody.innerHTML = "";

  for (const { id, receipt } of receipts) {
    const row = document.createElement("tr");

    const checkboxCell = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "receipt_ids";
    checkbox.value = id;
    checkbox.checked = selectedIds.has(id);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        selectedIds.add(id);
      } else {
        selectedIds.delete(id);
      }
      updateSelectedCount();
      updatePreview();
    });
    checkboxCell.appendChild(checkbox);

    const dateCell = document.createElement("td");
    dateCell.textContent = receipt.date;

    const shopCell = document.createElement("td");
    shopCell.textContent = receipt.store_name;

    row.appendChild(checkboxCell);
    row.appendChild(dateCell);
    row.appendChild(shopCell);
    tbody.appendChild(row);
  }
}

/**
 * Reads the `#filter-date-from`/`#filter-date-to` inputs and, if either is
 * set, appends them as `date_from`/`date_to` query params. Fetches
 * `GET /api/receipts` (optionally filtered), stores the parsed JSON in the
 * module-level `allReceipts`, and passes it to `renderList` to redraw the
 * table.
 */
function refreshList() {
  const dateFrom = document.getElementById("filter-date-from").value;
  const dateTo = document.getElementById("filter-date-to").value;
  const params = new URLSearchParams();
  if (dateFrom) {
    params.set("date_from", dateFrom);
  }
  if (dateTo) {
    params.set("date_to", dateTo);
  }
  const query = params.toString();

  fetch(`/api/receipts${query ? `?${query}` : ""}`)
    .then((response) => response.json())
    .then((data) => {
      allReceipts = data;
      renderList(allReceipts);
    });
}

/**
 * Uploads a single `file` to `POST /api/receipts/upload` as multipart form
 * data (field name `file`) and returns the fetch promise. On a non-OK
 * response, builds an error label starting with the HTTP status code and,
 * if the JSON body has a `detail.error` string (the short label the
 * backend attaches for known failure modes like "gemini outage" or
 * "no text"), appends it as `"<status>, <error>"`; if the body isn't JSON
 * or lacks that field, the label stays just the status code. Throws an
 * `Error` with that label so callers (see `uploadReceipts`) can report
 * per-file failure reasons.
 */
function uploadReceipt(file) {
  const formData = new FormData();
  formData.append("file", file);

  return fetch("/api/receipts/upload", {
    method: "POST",
    body: formData,
  }).then(async (response) => {
    if (!response.ok) {
      let label = `${response.status}`;
      try {
        const body = await response.json();
        if (body.detail && typeof body.detail === "object" && body.detail.error) {
          label = `${response.status}, ${body.detail.error}`;
        }
      } catch {
        // response body wasn't JSON; fall back to the status code alone
      }
      throw new Error(label);
    }
  });
}

/**
 * Uploads a list/array-like of `files` one at a time (sequentially
 * `await`-ing each `uploadReceipt` call, not in parallel), updating
 * `#upload-status` with `"Uploading i/N…"` before each one starts.
 * Successes increment a `succeeded` counter; failures push the thrown
 * error's message into `failedCodes` instead of aborting the batch, so
 * one bad file doesn't stop the rest from uploading. When the loop ends,
 * sets `#upload-status` to a summary (`"✓ N uploaded"`, or with a
 * `"✗ M failed (...)"` suffix listing each failure's label if any failed),
 * calls `refreshList()` once to pick up the newly uploaded receipts, and
 * clears the status text after a 4-second delay.
 */
async function uploadReceipts(files) {
  const statusEl = document.getElementById("upload-status");
  let succeeded = 0;
  const failedCodes = [];

  for (let i = 0; i < files.length; i++) {
    statusEl.textContent = `Uploading ${i + 1}/${files.length}…`;
    try {
      await uploadReceipt(files[i]);
      succeeded++;
    } catch (err) {
      failedCodes.push(err.message);
    }
  }

  statusEl.textContent =
    failedCodes.length === 0
      ? `✓ ${succeeded} uploaded`
      : `✓ ${succeeded} uploaded, ✗ ${failedCodes.length} failed (${failedCodes.join(", ")})`;
  refreshList();
  setTimeout(() => {
    statusEl.textContent = "";
  }, 4000);
}

/**
 * Clears and redraws `#preview-panel` from the `{ rows, grand_total }`
 * shape returned by `POST /api/receipts/preview`. If `rows` is missing or
 * empty, leaves the panel empty and returns early. Otherwise builds a
 * table with a fixed header row (`product_name`, `price`, `quantity`,
 * `price_per_item`, `user_id`, `date`, `shop_name`), one body row per
 * entry in `data.rows`, wraps the table in a `.table-wrap` div, and
 * appends a trailing `"Grand total: <data.grand_total>"` paragraph.
 */
function renderPreview(data) {
  const panel = document.getElementById("preview-panel");
  panel.innerHTML = "";

  if (!data.rows || data.rows.length === 0) {
    return;
  }

  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  const headers = [
    "product_name",
    "price",
    "quantity",
    "price_per_item",
    "user_id",
    "date",
    "shop_name",
  ];
  for (const header of headers) {
    const th = document.createElement("th");
    th.textContent = header;
    headerRow.appendChild(th);
  }
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const row of data.rows) {
    const tr = document.createElement("tr");
    for (const value of row) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);

  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  wrap.appendChild(table);
  panel.appendChild(wrap);

  const total = document.createElement("p");
  total.className = "summary-row summary-total";
  total.textContent = `Grand total: ${data.grand_total}`;
  panel.appendChild(total);
}

/**
 * Debounced refresh of the receipt preview panel, triggered whenever the
 * selection changes (see `renderList`'s checkbox handler). Cancels any
 * pending `previewDebounceTimer`. If `selectedIds` is empty, immediately
 * clears `#preview-panel` and returns. Otherwise schedules, after a
 * 300ms delay, a `POST /api/receipts/preview` call with the selected ids
 * as a JSON array body, and passes the parsed response to
 * `renderPreview`.
 */
function updatePreview() {
  clearTimeout(previewDebounceTimer);

  if (selectedIds.size === 0) {
    document.getElementById("preview-panel").innerHTML = "";
    return;
  }

  previewDebounceTimer = setTimeout(() => {
    fetch("/api/receipts/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify([...selectedIds]),
    })
      .then((response) => response.json())
      .then((data) => renderPreview(data));
  }, 300);
}

/**
 * Updates `#selected-count`'s text to `"<N> selected"` based on the
 * current size of `selectedIds`, and toggles `#delete-btn`'s `disabled`
 * state so it's only clickable when at least one receipt is selected.
 */
function updateSelectedCount() {
  document.getElementById("selected-count").textContent =
    `${selectedIds.size} selected`;
  document.getElementById("delete-btn").disabled = selectedIds.size === 0;
}

/**
 * Handles the "Delete selected" button click. Returns immediately if
 * `selectedIds` is empty, or if the user cancels a native `confirm()`
 * dialog asking them to confirm deleting `selectedIds.size` receipt(s).
 * Otherwise `POST`s the selected ids as JSON to `/api/receipts/delete`;
 * on a non-OK response throws an `Error` (unhandled — surfaces as a
 * console error), and on success clears `selectedIds`, calls
 * `updateSelectedCount()`, empties `#preview-panel`, and calls
 * `refreshList()` to reflect the deletion.
 */
function deleteSelected() {
  if (selectedIds.size === 0) {
    return;
  }
  if (!confirm(`Delete ${selectedIds.size} receipt(s)? This cannot be undone.`)) {
    return;
  }

  fetch("/api/receipts/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify([...selectedIds]),
  }).then((response) => {
    if (!response.ok) {
      throw new Error("Delete failed");
    }
    selectedIds.clear();
    updateSelectedCount();
    document.getElementById("preview-panel").innerHTML = "";
    refreshList();
  });
}

refreshList();

document.getElementById("reload-btn").addEventListener("click", refreshList);

document.getElementById("delete-btn").addEventListener("click", deleteSelected);

document.getElementById("filter-date-from").addEventListener("change", refreshList);
document.getElementById("filter-date-to").addEventListener("change", refreshList);

/**
 * `change` handler for `#upload-input`. Snapshots `event.target.files`
 * (a live `FileList`) into a plain array before resetting
 * `event.target.value` — clearing the input's value empties the live
 * `FileList` in place, so the copy must happen first or a multi-file
 * batch would lose its remaining files mid-upload. Resetting the value
 * also ensures re-selecting the same file(s) later still fires `change`.
 * If any files were selected, hands the array off to `uploadReceipts`.
 */
document.getElementById("upload-input").addEventListener("change", (event) => {
  const files = Array.from(event.target.files);
  event.target.value = "";
  if (files.length > 0) {
    uploadReceipts(files);
  }
});
