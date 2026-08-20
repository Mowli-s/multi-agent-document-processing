from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class InvoiceData(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None

    currency: str | None = None

    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None

    payment_terms: str | None = None

    line_items: list[InvoiceLineItem] = Field(default_factory=list)