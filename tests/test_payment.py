"""
Unit tests for Fetch.ai Payment Protocol Service.
Verifies pay-per-task pricing, invoice generation, review cards, duplicate payment protection,
and on-chain verification handling.
"""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest

from db.connection import get_db_session
from db.models import TransactionRef
from payment.models import PaymentInvoice, PaymentStatus, PaymentVerificationResult
from payment.service import PaymentService, SUBUNITS_PER_FET


@pytest.fixture
def payment_svc():
    return PaymentService(merchant_wallet="fetch1r5lk0kkhgrp4ep8n57635fwrz428fyc3lfyjqa")


def test_calculate_price_free_queries(payment_svc):
    """Basic utility requests should be free (0.0 FET)."""
    assert payment_svc.calculate_price("ping") == 0.0
    assert payment_svc.calculate_price("status") == 0.0
    assert payment_svc.calculate_price("info") == 0.0
    assert payment_svc.calculate_price("help") == 0.0


def test_calculate_price_premium_task(payment_svc):
    """Autonomous execution and valuation tasks require a fee."""
    assert payment_svc.calculate_price("Calculate portfolio valuation for 1000 FET") == 0.05
    assert payment_svc.calculate_price("Fetch live telemetry and execute analysis") == 0.05


def test_create_invoice(payment_svc):
    """Test generating a pay-per-task invoice."""
    invoice = payment_svc.create_invoice(
        task_id="task-42",
        task_name="Portfolio Valuation Task",
        payer_address="fetch1testuser99999",
    )
    assert isinstance(invoice, PaymentInvoice)
    assert invoice.task_id == "task-42"
    assert invoice.amount_fet == 0.05
    assert invoice.amount_subunits == int(0.05 * SUBUNITS_PER_FET)
    assert invoice.merchant_wallet == "fetch1r5lk0kkhgrp4ep8n57635fwrz428fyc3lfyjqa"
    assert invoice.status == PaymentStatus.REVIEW_REQUESTED
    assert invoice.payer_address == "fetch1testuser99999"


def test_generate_review_card(payment_svc):
    """Test creating an ACP review card for explicit user approval."""
    invoice = payment_svc.create_invoice(task_id="task-88", task_name="Weather & Pricing Audit")
    review_card = payment_svc.generate_review_card(invoice)

    assert review_card.type == "metadata"
    data = review_card.metadata
    assert data["content_type"] == "asi_card"
    assert data["card_type"] == "review"
    card_data = json.loads(data["data"])
    assert card_data["task_id"] == "task-88"
    assert card_data["fee_fet"] == 0.05


@pytest.mark.asyncio
async def test_duplicate_payment_protection(payment_svc):
    """Test that a transaction hash cannot be spent twice."""
    test_tx = f"TX_HASH_PREVIOUSLY_SPENT_{uuid4().hex[:12].upper()}"

    # Pre-seed database with transaction reference
    async with get_db_session() as session:
        existing_tx = TransactionRef(
            tx_hash=test_tx,
            task_id="task-old",
            sender_wallet="fetch1sender",
            recipient_wallet="fetch1r5lk0kkhgrp4ep8n57635fwrz428fyc3lfyjqa",
            amount="0.05",
            denom="atestfet",
            status="confirmed",
        )
        session.add(existing_tx)
        await session.commit()

    # Attempt to verify the same tx hash again
    result = await payment_svc.verify_transaction(
        tx_hash=test_tx,
        expected_amount_fet=0.05,
        task_id="task-new",
    )

    assert result.verified is False
    assert result.status == PaymentStatus.DUPLICATE_REJECTED
    assert "Duplicate payment rejected" in result.error


@pytest.mark.asyncio
async def test_on_chain_verification_failure_handling(payment_svc):
    """Ensure that failed or invalid transactions are never simulated as successful."""
    # When ledger client query raises an error
    with patch.object(payment_svc.ledger_client, "query_tx", side_effect=Exception("Transaction not found on testnet")):
        result = await payment_svc.verify_transaction(
            tx_hash=f"TX_HASH_NONEXISTENT_{uuid4().hex[:12].upper()}",
            expected_amount_fet=0.05,
            task_id="task-102",
        )

        assert result.verified is False
        assert result.status == PaymentStatus.FAILED
        assert "Transaction not found on testnet" in result.error


@pytest.mark.asyncio
async def test_on_chain_verification_success(payment_svc):
    """Test successful verification when ledger confirms transaction."""
    unique_tx = f"TX_HASH_VALID_TESTNET_{uuid4().hex[:12].upper()}"

    mock_tx_resp = MagicMock()
    mock_tx_resp.is_successful = MagicMock(return_value=True)
    mock_tx_resp.height = 1234567

    with patch.object(payment_svc.ledger_client, "query_tx", return_value=mock_tx_resp):
        result = await payment_svc.verify_transaction(
            tx_hash=unique_tx,
            expected_amount_fet=0.05,
            task_id="task-200",
            payer_address="fetch1sender123",
        )

        assert result.verified is True
        assert result.status == PaymentStatus.VERIFIED
        assert result.tx_hash == unique_tx
        assert result.block_height == 1234567

        # Verify it was recorded in DB
        async with get_db_session() as session:
            from sqlalchemy import select
            stmt = select(TransactionRef).where(TransactionRef.tx_hash == unique_tx)
            stored = (await session.execute(stmt)).scalar_one_or_none()
            assert stored is not None
            assert stored.amount == "0.05"
