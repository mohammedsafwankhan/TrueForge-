"""
Response and Execution Result Models.
Defines domain response structures returned by agent services.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from uagents import Model


class AgentPreviewInfo(Model):
    """
    Preview diagnostics returned on HTTP GET / for browser inspection.
    """

    name: str
    address: str
    wallet_address: str
    status: str
    version: str
    network: str
    protocol: str
    manifest_digest: str
    inspector_url: str


class AgentHealthInfo(Model):
    """
    Health check status response for monitoring and uptime probes.
    """

    status: str
    uptime_seconds: float
    timestamp: str
    details: str


class WebChatResponse(Model):
    """Structured response returned to frontend client."""

    reply: str
    session_id: str
    action: str
    fee_fet: float = 0.0
    has_card: bool = False
    card_type: str = ""
    card_title: str = ""
    card_payload: str = ""
    verification_status: str = "PASSED"


class WebPaymentResponse(Model):
    """Structured payment verification returned to frontend client."""

    verified: bool
    status: str
    tx_hash: str = ""
    block_height: int = 0
    message: str




class ResponseStatus(str, Enum):
    """Execution status for agent response."""

    ACKNOWLEDGED = "acknowledged"
    PROCESSED = "processed"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    IGNORED_DUPLICATE = "ignored_duplicate"
    ERROR = "error"


class ExecutionResult(BaseModel):
    """
    Structured outcome of business logic execution.
    """

    success: bool = True
    action_performed: str = "general_response"
    details: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class AgentStructuredResponse(BaseModel):
    """
    Production-grade structured agent response.
    Encapsulates message lifecycle state, content, and session tracking.
    """

    response_id: UUID = Field(default_factory=uuid4)
    status: ResponseStatus = Field(default=ResponseStatus.PROCESSED)
    sender_address: str = Field(description="Target recipient address")
    session_id: UUID | None = Field(default=None, description="Active session ID if applicable")
    reply_text: str | None = Field(default=None, description="Primary human- or agent-readable text")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timezone-aware UTC timestamp of generation",
    )
    execution_result: ExecutionResult = Field(default_factory=ExecutionResult)
    metadata: dict[str, Any] = Field(default_factory=dict)
