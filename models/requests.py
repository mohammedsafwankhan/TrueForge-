"""
Request and Inbound Message Context Models.
Represents parsed, validated message context decoupled from transport layers.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SessionAction(str, Enum):
    """Identified session lifecycle action in incoming message."""

    NONE = "none"
    START = "start"
    END = "end"


class InboundMessageContext(BaseModel):
    """
    Context extracted and validated from an incoming transport message.
    """

    sender: str = Field(description="Cryptographic address of the sender")
    msg_id: UUID = Field(description="Unique message identifier")
    timestamp: datetime = Field(description="Timezone-aware timestamp of the message")
    session_action: SessionAction = Field(
        default=SessionAction.NONE,
        description="Session boundary event detected in content",
    )
    extracted_text: list[str] = Field(
        default_factory=list,
        description="Extracted text fragments from all TextContent blocks",
    )
    raw_content_types: list[str] = Field(
        default_factory=list,
        description="Types of all content blocks received",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context parameters and metadata",
    )

    @property
    def combined_text(self) -> str:
        """Combine all extracted text blocks into a single query string."""
        return " ".join(self.extracted_text)

    @field_validator("timestamp")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime) -> datetime:
        """Enforce timezone-awareness for all message timestamps."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


from uagents import Model


class WebChatRequest(Model):
    """Payload for frontend chat interaction."""

    message: str
    session_id: str | None = None
    payer_address: str | None = None


class WebPaymentRequest(Model):
    """Payload for frontend on-chain payment submission."""

    tx_hash: str
    task_id: str
    expected_amount_fet: float = 0.05
    payer_address: str | None = None


    @property
    def combined_text(self) -> str:
        """Joined string of all text content blocks."""
        return "\n".join(self.extracted_text).strip()


class InboundContentSummary(BaseModel):
    """
    Summary breakdown of message content items for logging and metrics.
    """

    has_start_session: bool = False
    has_end_session: bool = False
    text_count: int = 0
    total_length: int = 0
