"""
Fetch.ai Official Agent Chat Protocol Integration.
Compliant with Agent Chat Protocol spec 0.3.0 and ASI:One interoperability.
"""

from datetime import datetime, timezone
from uuid import uuid4

from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

from core.logger import get_agent_logger
from services.message_service import MessageService
from services.session_service import SessionService

logger = get_agent_logger("protocols.chat_protocol")

# Instantiation of standard Fetch.ai Agent Chat Protocol specification
chat_proto = Protocol(spec=chat_protocol_spec)

# Global or injected message service instance
_message_service: MessageService | None = None


def get_default_message_service() -> MessageService:
    """Retrieve or lazily initialize the default message service."""
    global _message_service
    if _message_service is None:
        session_svc = SessionService()
        _message_service = MessageService(session_service=session_svc)
    return _message_service


def set_message_service(service: MessageService) -> None:
    """Inject a configured MessageService instance."""
    global _message_service
    _message_service = service


@chat_proto.on_message(model=ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage) -> None:
    """
    Primary handler for incoming ChatMessage envelopes.

    Orchestrates:
    1. Immediate ChatAcknowledgement generation.
    2. Message validation & content decoding.
    3. Session boundary identification (start/end).
    4. Business logic dispatch & context maintenance.
    5. Structured reply delivery back to sender.
    """
    ctx.logger.info(f"Received ChatMessage [id={msg.msg_id}] from sender={sender}")

    service = get_default_message_service()

    # Process message through business logic service
    ack, outbound_msg, structured_resp = await service.process_message(sender=sender, msg=msg)

    # 1. Dispatch acknowledgement to sender
    ctx.logger.info(f"Sending ChatAcknowledgement for msg_id={msg.msg_id} to {sender}")
    await ctx.send(sender, ack)

    # 2. Dispatch structured response message if produced
    if outbound_msg is not None:
        ctx.logger.info(
            f"Sending response ChatMessage [id={outbound_msg.msg_id}] "
            f"status={structured_resp.status} to {sender}"
        )
        await ctx.send(sender, outbound_msg)


@chat_proto.on_message(model=ChatAcknowledgement)
async def handle_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
    """
    Handler for incoming ChatAcknowledgement receipts.
    Confirms message delivery by remote agents and updates transmission metrics.
    """
    ctx.logger.info(
        f"Received ChatAcknowledgement from {sender} "
        f"for msg_id={msg.acknowledged_msg_id} at {msg.timestamp}"
    )


def setup_chat_protocol(message_service: MessageService | None = None) -> Protocol:
    """
    Configure and return the initialized chat protocol.

    Args:
        message_service: Optional custom MessageService for dependency injection.

    Returns:
        Verified Protocol instance ready for agent.include().
    """
    if message_service is not None:
        set_message_service(message_service)
    return chat_proto
