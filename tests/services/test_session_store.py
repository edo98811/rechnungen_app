from app.models.receipt import Receipt, ReceiptItem
from app.services import session_store


def _make_receipt(store_name: str = "REWE") -> Receipt:
    return Receipt(
        store_name=store_name,
        date="2026-07-01",
        items=[
            ReceiptItem(name="Milch", quantity=2, unit_price=1.19, total_price=2.38),
            ReceiptItem(name="Brot", quantity=1, unit_price=2.49, total_price=2.49),
        ],
        subtotal=4.87,
        tax_amount=0.34,
        total=5.21,
    )


def test_save_and_get_roundtrip():
    receipt = _make_receipt()
    receipt_id = session_store.save_receipt(receipt)

    stored = session_store.get_receipt(receipt_id)

    assert stored is not None
    assert stored.store_name == "REWE"
    assert stored.date == "2026-07-01"
    assert stored.user_id == "default"
    assert len(stored.items) == 2
    assert stored.items[0].name == "Milch"
    assert stored.items[0].quantity == 2
    assert stored.items[0].unit_price == 1.19
    assert stored.items[0].total_price == 2.38
    assert stored.items[1].name == "Brot"
    assert stored.subtotal == 4.87
    assert stored.tax_amount == 0.34
    assert stored.total == 5.21


def test_get_unknown_id_returns_none():
    assert session_store.get_receipt("nonexistent") is None


def test_list_receipts_returns_all_saved():
    id1 = session_store.save_receipt(_make_receipt("REWE"))
    id2 = session_store.save_receipt(_make_receipt("Aldi"))
    id3 = session_store.save_receipt(_make_receipt("Lidl"))

    all_receipts = session_store.list_receipts()

    assert [rid for rid, _ in all_receipts] == [id1, id2, id3]
    assert [r.store_name for _, r in all_receipts] == ["REWE", "Aldi", "Lidl"]


def test_migration_idempotent_on_reopen():
    conn1 = session_store._get_connection()
    conn1.close()

    # Reopening against the same db file should not error and the schema
    # should still be usable.
    conn2 = session_store._get_connection()
    try:
        version = conn2.execute("PRAGMA user_version").fetchone()[0]
        assert version == len(session_store._MIGRATIONS)
        conn2.execute("SELECT COUNT(*) FROM receipts").fetchone()
    finally:
        conn2.close()


def test_data_survives_reconnect():
    receipt = _make_receipt("Netto")
    receipt_id = session_store.save_receipt(receipt)

    # No connection object is held onto between the save above and the get
    # below - _get_connection() opens (and migrates) a fresh connection each
    # time, proving persistence lives in the file, not in-memory state.
    stored = session_store.get_receipt(receipt_id)

    assert stored is not None
    assert stored.store_name == "Netto"
