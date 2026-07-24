import sqlite3
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.models.receipt import Receipt, ReceiptItem, StoredReceipt

_MIGRATIONS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS receipts (
        id           TEXT PRIMARY KEY,
        user_id      TEXT NOT NULL DEFAULT 'default',
        store_name   TEXT NOT NULL,
        date         TEXT NOT NULL,
        subtotal     REAL NOT NULL,
        tax_amount   REAL NOT NULL,
        total        REAL NOT NULL,
        created_at   TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS receipt_items (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id   TEXT NOT NULL REFERENCES receipts(id),
        name         TEXT NOT NULL,
        quantity     REAL NOT NULL,
        unit_price   REAL NOT NULL,
        total_price  REAL NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_receipt_items_name ON receipt_items(name);
    CREATE INDEX IF NOT EXISTS idx_receipts_date ON receipts(date);
    CREATE INDEX IF NOT EXISTS idx_receipts_user_id ON receipts(user_id);
    """,
    # future schema changes get appended here, never edited in place
]


def _migrate(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for i, sql in enumerate(_MIGRATIONS[current:], start=current):
        conn.executescript(sql)
        conn.execute(f"PRAGMA user_version = {i + 1}")
    conn.commit()


def _get_connection() -> sqlite3.Connection:
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    _migrate(conn)
    return conn


def save_receipt(receipt: Receipt) -> str:
    receipt_id = uuid4().hex
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO receipts
                    (id, user_id, store_name, date, subtotal, tax_amount, total)
                VALUES (?, 'default', ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    receipt.store_name,
                    receipt.date,
                    receipt.subtotal,
                    receipt.tax_amount,
                    receipt.total,
                ),
            )
            conn.executemany(
                """
                INSERT INTO receipt_items
                    (receipt_id, name, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        receipt_id,
                        item.name,
                        item.quantity,
                        item.unit_price,
                        item.total_price,
                    )
                    for item in receipt.items
                ],
            )
    finally:
        conn.close()

    return receipt_id


def _fetch_items(conn: sqlite3.Connection, receipt_id: str) -> list[ReceiptItem]:
    rows = conn.execute(
        """
        SELECT name, quantity, unit_price, total_price
        FROM receipt_items
        WHERE receipt_id = ?
        ORDER BY id
        """,
        (receipt_id,),
    ).fetchall()
    return [
        ReceiptItem(
            name=name,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
        )
        for name, quantity, unit_price, total_price in rows
    ]


def get_receipt(receipt_id: str) -> StoredReceipt | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            """
            SELECT store_name, date, subtotal, tax_amount, total, user_id
            FROM receipts
            WHERE id = ?
            """,
            (receipt_id,),
        ).fetchone()
        if row is None:
            return None

        store_name, date, subtotal, tax_amount, total, user_id = row
        items = _fetch_items(conn, receipt_id)
    finally:
        conn.close()

    return StoredReceipt(
        store_name=store_name,
        date=date,
        items=items,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
        user_id=user_id,
    )


def delete_receipt(receipt_id: str) -> bool:
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                "DELETE FROM receipt_items WHERE receipt_id = ?", (receipt_id,)
            )
            cursor = conn.execute(
                "DELETE FROM receipts WHERE id = ?", (receipt_id,)
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def list_receipts() -> list[tuple[str, StoredReceipt]]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, store_name, date, subtotal, tax_amount, total, user_id
            FROM receipts
            ORDER BY rowid
            """
        ).fetchall()

        results: list[tuple[str, StoredReceipt]] = []
        for receipt_id, store_name, date, subtotal, tax_amount, total, user_id in rows:
            items = _fetch_items(conn, receipt_id)
            results.append(
                (
                    receipt_id,
                    StoredReceipt(
                        store_name=store_name,
                        date=date,
                        items=items,
                        subtotal=subtotal,
                        tax_amount=tax_amount,
                        total=total,
                        user_id=user_id,
                    ),
                )
            )
    finally:
        conn.close()

    return results
