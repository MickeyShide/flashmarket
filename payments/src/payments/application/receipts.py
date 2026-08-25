"""Strict local receipt contracts used before any fiscal integration is enabled."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from payments.application.contracts import (
    ProviderReceipt,
    ProviderReceiptCustomer,
    ProviderReceiptItem,
)

VATCode = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
PaymentSubject = Literal[
    "commodity",
    "excise",
    "job",
    "service",
    "gambling_bet",
    "gambling_prize",
    "lottery",
    "lottery_prize",
    "intellectual_activity",
    "payment",
    "agent_commission",
    "property_right",
    "non_operating_gain",
    "insurance_premium",
    "sales_tax",
    "resort_fee",
    "composite",
    "another",
]
PaymentMode = Literal[
    "full_prepayment",
    "partial_prepayment",
    "advance",
    "full_payment",
    "partial_payment",
    "credit",
    "credit_payment",
]
Measure = Literal[
    "piece",
    "gram",
    "kilogram",
    "ton",
    "centimeter",
    "decimeter",
    "meter",
    "square_centimeter",
    "square_decimeter",
    "square_meter",
    "milliliter",
    "liter",
    "cubic_meter",
    "kilowatt_hour",
    "gigacalorie",
    "day",
    "hour",
    "minute",
    "second",
    "kilobyte",
    "megabyte",
    "gigabyte",
    "terabyte",
    "another",
]

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE = re.compile(r"^\+[1-9]\d{7,14}$")


class ReceiptCustomer(BaseModel):
    """Customer contact accepted by the YooKassa receipt contract."""

    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=16)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def validate_contact(self) -> ReceiptCustomer:
        if not self.email and not self.phone:
            raise ValueError("receipt customer email or phone is required")
        if self.email and not _EMAIL.fullmatch(self.email):
            raise ValueError("receipt customer email is invalid")
        if self.phone and not _PHONE.fullmatch(self.phone):
            raise ValueError("receipt customer phone must be E.164")
        return self


class ReceiptItem(BaseModel):
    """One immutable receipt line with an exact kopeck total."""

    description: str = Field(min_length=1, max_length=128)
    quantity: Annotated[Decimal, Field(gt=0, decimal_places=3)]
    unit_amount: int = Field(gt=0)
    vat_code: VATCode
    payment_subject: PaymentSubject
    payment_mode: PaymentMode
    measure: Measure

    def total_kopecks(self) -> int:
        total = self.quantity * self.unit_amount
        if total != total.to_integral_value():
            raise ValueError("receipt item total must resolve to exact kopecks")
        return int(total)


class ReceiptSnapshot(BaseModel):
    """Validated immutable payload from which a fiscal receipt can be generated."""

    currency: Literal["RUB"] = "RUB"
    total_amount: int = Field(gt=0)
    items: list[ReceiptItem] = Field(min_length=1, max_length=80)
    customer: ReceiptCustomer | None = None

    @model_validator(mode="after")
    def validate_total(self) -> ReceiptSnapshot:
        if sum(item.total_kopecks() for item in self.items) != self.total_amount:
            raise ValueError("receipt items must exactly equal the payment amount")
        return self

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json", exclude_none=True),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def content_hash(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()


def snapshot_from_order_event(payload: dict[str, object]) -> ReceiptSnapshot:
    """Build a safe exact-total line when older events lack a receipt snapshot."""
    explicit = payload.get("receipt_snapshot")
    if isinstance(explicit, dict):
        return ReceiptSnapshot.model_validate(explicit)
    amount = int(str(payload["amount"]))
    currency = str(payload.get("currency", "RUB"))
    if currency != "RUB":
        raise ValueError("receipt currency must be RUB")
    return ReceiptSnapshot(
        currency="RUB",
        total_amount=amount,
        items=[
            ReceiptItem(
                description=str(payload.get("product_name") or "FlashMarket order")[:128],
                quantity=Decimal(1),
                unit_amount=amount,
                vat_code=1,
                payment_subject="commodity",
                payment_mode="full_payment",
                measure="piece",
            )
        ],
    )


def provider_receipt_from_snapshot(
    snapshot: ReceiptSnapshot,
    *,
    total_amount: int | None = None,
) -> ProviderReceipt:
    """Convert frozen fiscal input to an exact provider-neutral receipt."""
    if snapshot.customer is None:
        raise ValueError("receipt customer contact is required")
    requested_total = snapshot.total_amount if total_amount is None else total_amount
    if requested_total <= 0:
        raise ValueError("receipt total must be positive")

    if requested_total == snapshot.total_amount:
        items = tuple(
            ProviderReceiptItem(
                description=item.description,
                quantity=item.quantity,
                amount=item.unit_amount,
                vat_code=item.vat_code,
                payment_subject=item.payment_subject,
                payment_mode=item.payment_mode,
                measure=item.measure,
            )
            for item in snapshot.items
        )
    else:
        if len(snapshot.items) != 1:
            raise ValueError("partial receipt allocation requires one original item")
        source = snapshot.items[0]
        items = (
            ProviderReceiptItem(
                description=source.description,
                quantity=Decimal(1),
                amount=requested_total,
                vat_code=source.vat_code,
                payment_subject=source.payment_subject,
                payment_mode=source.payment_mode,
                measure=source.measure,
            ),
        )

    actual_total = sum(item.quantity * item.amount for item in items)
    if actual_total != Decimal(requested_total):
        raise ValueError("provider receipt items must exactly equal the requested total")
    return ProviderReceipt(
        customer=ProviderReceiptCustomer(
            email=snapshot.customer.email,
            phone=snapshot.customer.phone,
        ),
        currency=snapshot.currency,
        items=items,
    )
