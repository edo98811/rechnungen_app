from uuid import uuid4

from app.models.receipt import Receipt

_receipts: dict[str, Receipt] = {}


def save_receipt(receipt: Receipt) -> str:
    receipt_id = uuid4().hex
    _receipts[receipt_id] = receipt
    return receipt_id


def get_receipt(receipt_id: str) -> Receipt | None:
    return _receipts.get(receipt_id)


def list_receipts() -> list[tuple[str, Receipt]]:
    return list(_receipts.items())
