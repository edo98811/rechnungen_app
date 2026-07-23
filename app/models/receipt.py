from pydantic import BaseModel


class ReceiptItem(BaseModel):
    name: str
    quantity: float
    unit_price: float
    total_price: float


class Receipt(BaseModel):
    store_name: str
    date: str
    items: list[ReceiptItem]
    subtotal: float
    tax_amount: float
    total: float


class StoredReceipt(Receipt):
    """A Receipt as persisted/retrieved from storage, tagged with its owner.

    Kept separate from Receipt (rather than adding user_id directly to it)
    because Receipt also doubles as the Claude extraction output_format
    schema (see app/services/extraction.py) — a user_id field there would
    be something Claude has no way to derive from a receipt photo.
    """

    user_id: str = "default"
