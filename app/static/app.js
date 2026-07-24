let allReceipts = [];
const selectedIds = new Set();

let previewDebounceTimer = null;

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

function refreshList() {
  fetch("/api/receipts")
    .then((response) => response.json())
    .then((data) => {
      allReceipts = data;
      renderList(allReceipts);
    });
}

function uploadReceipt(file) {
  const statusEl = document.getElementById("upload-status");
  const formData = new FormData();
  formData.append("file", file);

  statusEl.textContent = "Uploading…";

  fetch("/api/receipts/upload", {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Upload failed");
      }
      statusEl.textContent = "✓ Upload successful";
      refreshList();
      setTimeout(() => {
        statusEl.textContent = "";
      }, 4000);
    })
    .catch(() => {
      statusEl.textContent = "✗ Upload failed";
    });
}

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

function updateSelectedCount() {
  document.getElementById("selected-count").textContent =
    `${selectedIds.size} selected`;
}

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

document.getElementById("upload-input").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) {
    uploadReceipt(file);
  }
});
