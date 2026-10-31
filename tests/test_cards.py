"""
Unit tests for ASI Interactive Cards and ACP MetadataContent serialization.
Tests compliance with official ASI Interactive Cards specifications.
"""

import json
import pytest
from uagents_core.contrib.protocols.chat import MetadataContent

from cards.card_factory import CardFactory
from cards.models import ASICard, CardAction, CardField, CardType


def test_card_type_enum():
    """Verify all 6 official interactive card types are defined."""
    assert CardType.INPUT_FORM.value == "input_form"
    assert CardType.SELECTION.value == "selection"
    assert CardType.DETAIL.value == "detail"
    assert CardType.REVIEW.value == "review"
    assert CardType.CONFIRMATION.value == "confirmation"
    assert CardType.RESULT.value == "result"
    assert len(CardType) == 6


def test_input_form_card():
    """Test generating an input form card."""
    meta = CardFactory.create_input_form_card(
        title="Custom Form",
        description="Fill out the params",
        fields=[
            CardField(field_id="sym", label="Token Symbol", value="FET"),
            CardField(field_id="amt", label="Amount", field_type="number", value=500),
        ],
    )
    assert isinstance(meta, MetadataContent)
    assert meta.type == "metadata"
    meta_dict = meta.metadata
    assert meta_dict["content_type"] == "asi_card"
    assert meta_dict["card_type"] == CardType.INPUT_FORM.value
    assert meta_dict["title"] == "Custom Form"

    fields = json.loads(meta_dict["fields"])
    actions = json.loads(meta_dict["actions"])
    assert len(fields) == 2
    assert fields[0]["field_id"] == "sym"
    assert len(actions) >= 1


def test_selection_card():
    """Test generating an interactive selection card."""
    meta = CardFactory.create_selection_card(
        title="Select Capability",
        description="Choose a tool",
        options=[
            {"id": "opt1", "label": "Option 1", "desc": "First"},
            {"id": "opt2", "label": "Option 2", "desc": "Second"},
        ],
    )
    assert isinstance(meta, MetadataContent)
    meta_dict = meta.metadata
    assert meta_dict["card_type"] == CardType.SELECTION.value
    actions = json.loads(meta_dict["actions"])
    assert len(actions) == 2
    assert actions[0]["payload"] == {"service": "opt1"}


def test_detail_card():
    """Test generating an interactive detail card."""
    telemetry = {"temperature_c": 22.5, "wind_speed_kmh": 14.2, "status": "nominal"}
    meta = CardFactory.create_detail_card(
        title="Weather Telemetry",
        description="Berlin Sensor Hub",
        details=telemetry,
        source="Open-Meteo",
    )
    assert isinstance(meta, MetadataContent)
    meta_dict = meta.metadata
    assert meta_dict["card_type"] == CardType.DETAIL.value
    assert meta_dict["title"] == "Weather Telemetry"
    card_data = json.loads(meta_dict["data"])
    assert card_data["source"] == "Open-Meteo"

    fields = json.loads(meta_dict["fields"])
    field_keys = [f["field_id"] for f in fields]
    assert "temperature_c" in field_keys
    assert "wind_speed_kmh" in field_keys


def test_review_card():
    """Test generating a review and payment authorization screen."""
    meta = CardFactory.create_review_card(
        task_id="task-999",
        task_summary="Autonomous Valuation Analysis",
        fee_fet=0.05,
        recipient_wallet="fetch1r5lk0kkhgrp4ep8n57635fwrz428fyc3lfyjqa",
    )
    assert isinstance(meta, MetadataContent)
    meta_dict = meta.metadata
    assert meta_dict["card_type"] == CardType.REVIEW.value
    card_data = json.loads(meta_dict["data"])
    assert card_data["task_id"] == "task-999"
    assert card_data["fee_fet"] == 0.05

    actions = json.loads(meta_dict["actions"])
    assert len(actions) == 2
    assert any(a["action_id"] == "authorize_payment" for a in actions)
    assert any(a["action_id"] == "reject_payment" for a in actions)


def test_confirmation_card():
    """Test generating an interactive confirmation card."""
    meta = CardFactory.create_confirmation_card(
        title="Payment Authorized",
        message="Transaction confirmed on Fetch.ai Dorado Testnet",
        tx_hash="8A9B0C1D2E3F4567890ABCDEF",
        task_id="task-101",
    )
    assert isinstance(meta, MetadataContent)
    meta_dict = meta.metadata
    assert meta_dict["card_type"] == CardType.CONFIRMATION.value
    card_data = json.loads(meta_dict["data"])
    assert card_data["tx_hash"] == "8A9B0C1D2E3F4567890ABCDEF"

    fields = json.loads(meta_dict["fields"])
    field_ids = [f["field_id"] for f in fields]
    assert "tx_hash" in field_ids
    assert "status" in field_ids


def test_result_card():
    """Test generating an interactive result card with verification status."""
    res_data = {"usd_price": 1.45, "calculated_valuation": 1450.0, "asset": "fetch-ai"}
    meta = CardFactory.create_result_card(
        title="Portfolio Valuation Result",
        summary="Valuation calculated and verified via multi-agent consensus",
        data=res_data,
        verification_passed=True,
    )
    assert isinstance(meta, MetadataContent)
    meta_dict = meta.metadata
    assert meta_dict["card_type"] == CardType.RESULT.value

    fields = json.loads(meta_dict["fields"])
    assert fields[1]["value"] == "PASSED (Quality Verified)"
    card_data = json.loads(meta_dict["data"])
    assert card_data["calculated_valuation"] == 1450.0


def test_card_serialization_roundtrip():
    """Test converting ASICard to metadata dict and verifying roundtrip deserialization."""
    card = ASICard(
        card_type=CardType.INPUT_FORM,
        title="Roundtrip Test",
        description="Testing schema integrity",
        fields=[CardField(field_id="test_f", label="Test Field", value="abc")],
        actions=[CardAction(action_id="act_1", label="Submit", style="primary")],
    )
    meta_dict = card.to_metadata_dict()
    assert meta_dict["content_type"] == "asi_card"
    assert meta_dict["version"] == "1.0.0"
    assert meta_dict["card_type"] == "input_form"
    assert meta_dict["title"] == "Roundtrip Test"

    # Test roundtrip deserialization
    restored = ASICard.from_metadata_dict(meta_dict)
    assert restored.title == "Roundtrip Test"
    assert restored.card_type == CardType.INPUT_FORM
    assert len(restored.fields) == 1
    assert restored.fields[0].field_id == "test_f"
    assert len(restored.actions) == 1
    assert restored.actions[0].action_id == "act_1"
