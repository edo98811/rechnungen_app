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
