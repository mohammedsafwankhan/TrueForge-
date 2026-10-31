"""
Fetch.ai Payment Protocol Models.
Supports pay-per-task microtransactions, invoice generation, and on-chain verification.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    """Lifecycle status of a task payment."""

    PENDING = "pending"
    REVIEW_REQUESTED = "review_requested"
    AUTHORIZED = "authorized"
    VERIFIED = "verified"
    REJECTED = "rejected"
    FAILED = "failed"
    DUPLICATE_REJECTED = "duplicate_rejected"


class PaymentInvoice(BaseModel):
    """Invoice for a paid autonomous agent task."""

    invoice_id: UUID = Field(default_factory=uuid4)
    task_id: str
    task_name: str
    amount_fet: float
    denom: str = "atestfet"  # or 'afet' on mainnet
    amount_subunits: int  # 1 FET = 10^18 afet/atestfet
    merchant_wallet: str
    payer_address: str | None = None
    status: PaymentStatus = PaymentStatus.REVIEW_REQUESTED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaymentVerificationResult(BaseModel):
    """Outcome of on-chain ledger payment verification."""

    verified: bool
    tx_hash: str | None = None
    amount_fet: float = 0.0
    payer_address: str | None = None
    merchant_address: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    block_height: int | None = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
