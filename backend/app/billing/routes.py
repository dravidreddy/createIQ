"""
Billing Routes — Razorpay Integration

Handles credit-package purchases via Razorpay Orders API.
Flow: create-order → Razorpay Checkout (frontend) → verify-payment → credits added.
"""

import logging
import razorpay
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.config import get_settings
from app.schemas.base import CreatorResponse, wrap_response
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Credit Packages ────────────────────────────────────────────
CREDIT_PACKAGES = {
    "starter": {"credits": 50,  "amount_paise": 24900,  "label": "50 Credits",  "price": "₹249"},
    "popular": {"credits": 150, "amount_paise": 59900,  "label": "150 Credits", "price": "₹599"},
    "pro":     {"credits": 500, "amount_paise": 149900, "label": "500 Credits", "price": "₹1,499"},
}


def _get_razorpay_client() -> razorpay.Client:
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


# ─── Schemas ────────────────────────────────────────────────────
class CreateOrderRequest(BaseModel):
    package_id: str = Field(..., description="One of: starter, popular, pro")


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    package_id: str
    credits: int


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    status: str
    credits_added: int
    new_balance: int


# ─── Routes ─────────────────────────────────────────────────────

@router.get("/packages", response_model=CreatorResponse[dict])
async def get_packages(current_user: User = Depends(get_current_user)):
    """Return available credit packages."""
    return wrap_response({
        "packages": [
            {"id": k, **v} for k, v in CREDIT_PACKAGES.items()
        ],
        "credits_per_run": get_settings().credits_per_pipeline_run,
        "current_balance": current_user.credits,
    })


@router.post("/create-order", response_model=CreatorResponse[CreateOrderResponse])
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a Razorpay order for a credit package."""
    package = CREDIT_PACKAGES.get(request.package_id)
    if not package:
        raise HTTPException(status_code=400, detail=f"Unknown package: {request.package_id}")

    client = _get_razorpay_client()
    settings = get_settings()

    order_data = {
        "amount": package["amount_paise"],
        "currency": "INR",
        "receipt": f"criq_{current_user.id}_{request.package_id}",
        "notes": {
            "user_id": str(current_user.id),
            "package_id": request.package_id,
            "credits": str(package["credits"]),
        }
    }

    try:
        order = client.order.create(data=order_data)
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=502, detail="Payment gateway error")

    # Persist pending transaction
    txn = Transaction(
        user_id=str(current_user.id),
        razorpay_order_id=order["id"],
        amount_paise=package["amount_paise"],
        credits_purchased=package["credits"],
        status="pending",
    )
    await txn.insert()

    return wrap_response(CreateOrderResponse(
        order_id=order["id"],
        amount=package["amount_paise"],
        currency="INR",
        key_id=settings.razorpay_key_id,
        package_id=request.package_id,
        credits=package["credits"],
    ))


@router.post("/verify-payment", response_model=CreatorResponse[VerifyPaymentResponse])
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
):
    """Verify Razorpay payment signature and add credits."""
    client = _get_razorpay_client()

    # 1. Verify cryptographic signature
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": request.razorpay_order_id,
            "razorpay_payment_id": request.razorpay_payment_id,
            "razorpay_signature": request.razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        logger.warning(f"Signature verification failed for order {request.razorpay_order_id}")
        # Mark transaction failed
        txn = await Transaction.find_one(Transaction.razorpay_order_id == request.razorpay_order_id)
        if txn:
            txn.status = "failed"
            txn.updated_at = utc_now()
            await txn.save()
        raise HTTPException(status_code=400, detail="Payment verification failed")

    # 2. Find and update transaction
    txn = await Transaction.find_one(Transaction.razorpay_order_id == request.razorpay_order_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn.status == "success":
        # Idempotent — already processed
        return wrap_response(VerifyPaymentResponse(
            status="already_processed",
            credits_added=0,
            new_balance=current_user.credits,
        ))

    # 3. Mark transaction success
    txn.razorpay_payment_id = request.razorpay_payment_id
    txn.razorpay_signature = request.razorpay_signature
    txn.status = "success"
    txn.updated_at = utc_now()
    await txn.save()

    # 4. Add credits to user
    new_balance = current_user.credits + txn.credits_purchased
    await current_user.set({"credits": new_balance})

    logger.info(f"Payment verified: user={current_user.id}, credits_added={txn.credits_purchased}, new_balance={new_balance}")

    return wrap_response(VerifyPaymentResponse(
        status="success",
        credits_added=txn.credits_purchased,
        new_balance=new_balance,
    ))


@router.get("/history", response_model=CreatorResponse[list])
async def get_transaction_history(
    current_user: User = Depends(get_current_user),
):
    """Return the user's transaction history."""
    txns = await Transaction.find(
        Transaction.user_id == str(current_user.id),
        Transaction.status == "success",
    ).sort("-created_at").limit(20).to_list()

    return wrap_response([
        {
            "id": str(t.id),
            "credits": t.credits_purchased,
            "amount_paise": t.amount_paise,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
        }
        for t in txns
    ])
