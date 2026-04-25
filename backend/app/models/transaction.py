"""
Transaction Document — MongoDB / Beanie

Records all payment transactions from Razorpay.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class Transaction(Document):
    """A single credit-purchase transaction."""

    user_id: Indexed(str)  # type: ignore[valid-type]

    # Razorpay identifiers
    razorpay_order_id: str
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None

    # Financial
    amount_paise: int  # Amount in paise (₹500 = 50000)
    currency: str = "INR"
    credits_purchased: int

    # Status lifecycle: pending → success | failed
    status: str = Field(default="pending")  # pending | success | failed

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "transactions"
