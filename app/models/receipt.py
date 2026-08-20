from pydantic import BaseModel, Field


class ReceiptItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    price: float | None = None
    amount: float | None = None


class ReceiptData(BaseModel):
    merchant_name: str | None = None
    transaction_date: str | None = None

    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None

    currency: str | None = None

    items: list[ReceiptItem] = Field(default_factory=list)