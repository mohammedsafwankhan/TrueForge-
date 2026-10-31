"""
ASI Interactive Card Data Models.
Compliant with Fetch.ai Agent Chat Protocol (ACP) MetadataContent specifications.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CardType(str, Enum):
    """Officially supported ASI:One interactive card types."""

    INPUT_FORM = "input_form"
    SELECTION = "selection"
    DETAIL = "detail"
    REVIEW = "review"
    CONFIRMATION = "confirmation"
    RESULT = "result"


class CardAction(BaseModel):
    """Action button or interactive call-to-action on a card."""

    action_id: str
    label: str
    action_type: str = "submit"  # submit, cancel, navigate, external_link
    payload: dict[str, Any] = Field(default_factory=dict)
    style: str = "primary"  # primary, secondary, danger, success


class CardField(BaseModel):
    """Input or display field on a card."""

    field_id: str
    label: str
    field_type: str = "text"  # text, select, number, boolean, textarea
    value: Any | None = None
    options: list[str] | None = None
    required: bool = True
    placeholder: str | None = None


class ASICard(BaseModel):
    """
    Standard ASI Interactive Card container.
    Serialized into ACP MetadataContent for rendering inside ASI:One.
    """

    card_id: UUID = Field(default_factory=uuid4)
    card_type: CardType
    title: str
    description: str | None = None
    fields: list[CardField] = Field(default_factory=list)
    actions: list[CardAction] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_metadata_dict(self) -> dict[str, str]:
        """
        Convert card container into ACP MetadataContent dictionary format.
        Compliant with official ASI Interactive Cards schema where all metadata values are strings.
        """
        import json

        fields_data = [f.model_dump() for f in self.fields]
        actions_data = [a.model_dump() for a in self.actions]

        return {
            "content_type": "asi_card",
            "version": "1.0.0",
            "card_id": str(self.card_id),
            "card_type": self.card_type.value,
            "title": self.title,
            "card_title": self.title,
            "description": self.description or "",
            "card_description": self.description or "",
            "fields": json.dumps(fields_data),
            "actions": json.dumps(actions_data),
            "data": json.dumps(self.data),
            "card_payload": json.dumps(
                {
                    "fields": fields_data,
                    "actions": actions_data,
                    "data": self.data,
                }
            ),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_metadata_dict(cls, meta: dict[str, Any]) -> "ASICard":
        """Deserialize an ACP MetadataContent dictionary back into an ASICard."""
        import json

        card_type = CardType(meta.get("card_type", CardType.DETAIL.value))
        title = meta.get("title") or meta.get("card_title", "")
        description = meta.get("description") or meta.get("card_description", "")

        raw_fields = meta.get("fields", [])
        if isinstance(raw_fields, str):
            try:
                raw_fields = json.loads(raw_fields)
            except Exception:
                raw_fields = []

        raw_actions = meta.get("actions", [])
        if isinstance(raw_actions, str):
            try:
                raw_actions = json.loads(raw_actions)
            except Exception:
                raw_actions = []

        raw_data = meta.get("data", {})
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except Exception:
                raw_data = {}

        # If payload was serialized as json string
        if not raw_fields and not raw_actions and "card_payload" in meta:
            try:
                payload = json.loads(meta["card_payload"])
                raw_fields = payload.get("fields", raw_fields)
                raw_actions = payload.get("actions", raw_actions)
                raw_data = payload.get("data", raw_data)
            except Exception:
                pass

        fields = [CardField(**f) for f in raw_fields]
        actions = [CardAction(**a) for a in raw_actions]

        card_id = UUID(meta["card_id"]) if "card_id" in meta else uuid4()
        return cls(
            card_id=card_id,
            card_type=card_type,
            title=title,
            description=description,
            fields=fields,
            actions=actions,
            data=raw_data,
        )
