"""
ASI Interactive Card Factory.
Generates input forms, selection cards, detail cards, review screens, confirmation cards, and result cards.
"""

from typing import Any
from uuid import UUID

from uagents_core.contrib.protocols.chat import MetadataContent

from cards.models import ASICard, CardAction, CardField, CardType


class CardFactory:
    """
    Factory creating compliant ACP MetadataContent blocks for ASI:One interactive cards.
    """

    @staticmethod
    def wrap_in_metadata_content(card: ASICard) -> MetadataContent:
        """Wrap an ASICard container into ACP MetadataContent model."""
        return MetadataContent(type="metadata", metadata=card.to_metadata_dict())

    @classmethod
    def create_input_form_card(
        cls,
        title: str = "Configure Autonomous Task",
        description: str = "Provide parameters for multi-agent execution:",
        fields: list[CardField] | None = None,
        submit_action_id: str = "submit_task_params",
    ) -> MetadataContent:
        """Create an interactive Input Form card."""
        default_fields = fields or [
            CardField(
                field_id="token_id",
                label="Target Asset",
                field_type="select",
                value="fetch-ai",
                options=["fetch-ai", "ethereum", "bitcoin"],
                required=True,
            ),
            CardField(
                field_id="quantity",
                label="Quantity for Valuation",
                field_type="number",
                value=1000,
                required=True,
                placeholder="Enter token amount",
            ),
        ]
        actions = [
            CardAction(action_id=submit_action_id, label="Execute Analysis", action_type="submit", style="primary"),
            CardAction(action_id="cancel_action", label="Cancel", action_type="cancel", style="secondary"),
        ]
        card = ASICard(
            card_type=CardType.INPUT_FORM,
            title=title,
            description=description,
            fields=default_fields,
            actions=actions,
        )
        return cls.wrap_in_metadata_content(card)

    @classmethod
    def create_selection_card(
        cls,
        title: str = "Select Autonomous Service",
        description: str = "Choose a specialized capability to activate:",
        options: list[dict[str, str]] | None = None,
    ) -> MetadataContent:
        """Create an interactive Selection card."""
        choices = options or [
            {"id": "service_oracle", "label": "Crypto Pricing Oracle ($FET / $ETH / $BTC)", "desc": "Live market data"},
            {"id": "service_weather", "label": "Global Weather Telemetry", "desc": "Real-time meteorological metrics"},
            {"id": "service_mcp", "label": "Fetch.ai Network MCP Inspector", "desc": "Cosmos ledger telemetry"},
            {"id": "service_calc", "label": "Safe Computational Engine", "desc": "Mathematical evaluation"},
        ]
        actions = [
            CardAction(
                action_id=f"select_{item['id']}",
                label=item["label"],
                action_type="submit",
                payload={"service": item["id"]},
                style="primary",
            )
            for item in choices
        ]
        card = ASICard(
            card_type=CardType.SELECTION,
            title=title,
            description=description,
            actions=actions,
            data={"choices": choices},
        )
        return cls.wrap_in_metadata_content(card)

    @classmethod
    def create_detail_card(
        cls,
        title: str,
        description: str,
        details: dict[str, Any],
        source: str = "Verified Live Oracle",
    ) -> MetadataContent:
        """Create an interactive Detail view card."""
        fields = [CardField(field_id=k, label=k.replace("_", " ").title(), value=v) for k, v in details.items()]
        actions = [
            CardAction(action_id="refresh_data", label="Refresh Data", action_type="submit", style="secondary"),
            CardAction(action_id="dismiss", label="Done", action_type="cancel", style="primary"),
        ]
        card = ASICard(
            card_type=CardType.DETAIL,
            title=title,
            description=description,
            fields=fields,
            actions=actions,
            data={"source": source, "details": details},
        )
        return cls.wrap_in_metadata_content(card)

    @classmethod
    def create_review_card(
        cls,
        task_id: str,
        task_summary: str,
        fee_fet: float,
        recipient_wallet: str,
    ) -> MetadataContent:
        """Create an interactive Review Screen for task execution & payment authorization."""
        fields = [
            CardField(field_id="task_id", label="Task Identifier", value=task_id),
            CardField(field_id="summary", label="Operation Scope", value=task_summary),
            CardField(field_id="fee", label="Execution Fee", value=f"{fee_fet:.4f} FET"),
            CardField(field_id="recipient", label="Merchant Address", value=recipient_wallet),
            CardField(field_id="model", label="Payment Model", value="Pay-Per-Task (Microtransaction)"),
        ]
        actions = [
            CardAction(
                action_id="authorize_payment",
                label=f"Authorize Payment ({fee_fet:.4f} FET)",
                action_type="submit",
                payload={"task_id": task_id, "fee_fet": fee_fet, "recipient": recipient_wallet},
                style="success",
            ),
            CardAction(
                action_id="reject_payment",
                label="Decline",
                action_type="cancel",
                payload={"task_id": task_id},
                style="danger",
            ),
        ]
        card = ASICard(
            card_type=CardType.REVIEW,
            title="Review & Authorize Task Payment",
            description="Explicit authorization required before triggering paid autonomous execution:",
            fields=fields,
            actions=actions,
            data={"task_id": task_id, "fee_fet": fee_fet, "recipient": recipient_wallet},
        )
        return cls.wrap_in_metadata_content(card)

    @classmethod
    def create_confirmation_card(
        cls,
        title: str,
        message: str,
        tx_hash: str | None = None,
        task_id: str | None = None,
    ) -> MetadataContent:
        """Create an interactive Confirmation card."""
        fields = [
            CardField(field_id="status", label="Status", value="CONFIRMED"),
            CardField(field_id="message", label="Details", value=message),
        ]
        if tx_hash:
            fields.append(CardField(field_id="tx_hash", label="Ledger Tx Reference", value=tx_hash))

        actions = [
            CardAction(action_id="view_results", label="View Live Results", action_type="submit", style="primary"),
        ]
        card = ASICard(
            card_type=CardType.CONFIRMATION,
            title=title,
            description="Transaction and authorization confirmed on Fetch.ai ledger.",
            fields=fields,
            actions=actions,
            data={"tx_hash": tx_hash, "task_id": task_id},
        )
        return cls.wrap_in_metadata_content(card)

    @classmethod
    def create_result_card(
        cls,
        title: str,
        summary: str,
        data: dict[str, Any],
        verification_passed: bool = True,
    ) -> MetadataContent:
        """Create an interactive Result card."""
        fields = [
            CardField(field_id="summary", label="Outcome Summary", value=summary),
            CardField(
                field_id="verification",
                label="Verification Status",
                value="PASSED (Quality Verified)" if verification_passed else "WARNING (Verification Issues)",
            ),
        ]
        for k, v in data.items():
            fields.append(CardField(field_id=k, label=k.replace("_", " ").title(), value=str(v)))

        actions = [
            CardAction(action_id="export_json", label="Export JSON", action_type="submit", style="secondary"),
            CardAction(action_id="new_task", label="New Autonomous Task", action_type="submit", style="primary"),
        ]
        card = ASICard(
            card_type=CardType.RESULT,
            title=title,
            description="Execution complete. Verified by autonomous multi-agent pipeline.",
            fields=fields,
            actions=actions,
            data=data,
        )
        return cls.wrap_in_metadata_content(card)
