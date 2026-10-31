"""
Unit and Contract Tests for Fetch.ai Agent Chat Protocol Implementation.
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

from models.responses import ResponseStatus
from protocols.chat_protocol import chat_proto, handle_chat_ack, handle_chat_message, setup_chat_protocol
from services.message_service import MessageService
from services.session_service import SessionService
from tests.conftest import MockContext


class TestChatProtocolSpecification:
    """Tests verifying compliance with official Agent Chat Protocol specification."""

    def test_protocol_spec_properties(self) -> None:
        """Verify chat_protocol_spec name, version, and interactions."""
        assert chat_protocol_spec.name == "AgentChatProtocol"
        assert chat_protocol_spec.version == "0.3.0"
        assert ChatMessage in chat_protocol_spec.interactions
        assert ChatAcknowledgement in chat_protocol_spec.interactions[ChatMessage]

    def test_protocol_manifest_generation(self) -> None:
        """Verify protocol manifest compiles valid digests and interaction schemas."""
        proto = Protocol(spec=chat_protocol_spec)

        @proto.on_message(model=ChatMessage)
        async def _m(ctx: Context, sender: str, msg: ChatMessage):
            pass

        @proto.on_message(model=ChatAcknowledgement)
        async def _a(ctx: Context, sender: str, msg: ChatAcknowledgement):
            pass

        assert proto.verify() is True
        manifest = proto.manifest()
        assert manifest["metadata"]["name"] == "AgentChatProtocol"
        assert manifest["metadata"]["version"] == "0.3.0"
        assert "digest" in manifest["metadata"]
        assert len(manifest["models"]) == 2
        model_titles = [m["schema"]["title"] for m in manifest["models"]]
        assert "ChatMessage" in model_titles
        assert "ChatAcknowledgement" in model_titles

    def test_protocol_verification_failure_without_handlers(self) -> None:
        """Verify protocol verification fails if required spec handlers are not bound."""
        empty_proto = Protocol(spec=chat_protocol_spec)
        assert empty_proto.verify() is False


class TestChatProtocolExecutionFlow:
    """Tests covering message handling, acknowledgement, and deduplication flows."""

    @pytest.mark.asyncio
    async def test_handle_chat_message_acknowledges_and_replies(
        self,
        mock_context: MockContext,
        test_sender: str,
        sample_text_message: ChatMessage,
        message_service: MessageService,
    ) -> None:
        """Verify incoming message sends both ChatAcknowledgement and reply ChatMessage."""
        setup_chat_protocol(message_service=message_service)

        await handle_chat_message(
            ctx=mock_context,  # type: ignore
            sender=test_sender,
            msg=sample_text_message,
        )

        # Must have sent at least two messages: 1 ack + 1 reply
        assert len(mock_context.sent_messages) == 2

        # 1. Acknowledgement check
        ack_recipient, ack_payload = mock_context.sent_messages[0]
        assert ack_recipient == test_sender
        assert isinstance(ack_payload, ChatAcknowledgement)
        assert ack_payload.acknowledged_msg_id == sample_text_message.msg_id
        assert ack_payload.timestamp.tzinfo is not None

        # 2. Outbound message check
        reply_recipient, reply_payload = mock_context.sent_messages[1]
        assert reply_recipient == test_sender
        assert isinstance(reply_payload, ChatMessage)
        assert reply_payload.msg_id != sample_text_message.msg_id
        assert len(reply_payload.content) > 0
        assert isinstance(reply_payload.content[0], TextContent)

    @pytest.mark.asyncio
    async def test_duplicate_message_is_acknowledged_but_not_reprocessed(
        self,
        mock_context: MockContext,
        test_sender: str,
        sample_text_message: ChatMessage,
        message_service: MessageService,
    ) -> None:
        """Verify replay attack or duplicate delivery only sends ack and skips reprocessing."""
        setup_chat_protocol(message_service=message_service)

        # First delivery
        await handle_chat_message(
            ctx=mock_context,  # type: ignore
            sender=test_sender,
            msg=sample_text_message,
        )
        assert len(mock_context.sent_messages) == 2

        # Clear recorded sends
        mock_context.sent_messages.clear()

        # Second delivery of same msg_id
        await handle_chat_message(
            ctx=mock_context,  # type: ignore
            sender=test_sender,
            msg=sample_text_message,
        )

        # Only 1 message sent: the ChatAcknowledgement; reply is suppressed
        assert len(mock_context.sent_messages) == 1
        recipient, ack = mock_context.sent_messages[0]
        assert recipient == test_sender
        assert isinstance(ack, ChatAcknowledgement)
        assert ack.acknowledged_msg_id == sample_text_message.msg_id

    @pytest.mark.asyncio
    async def test_handle_chat_acknowledgement(
        self,
        mock_context: MockContext,
        test_sender: str,
    ) -> None:
        """Verify ChatAcknowledgement handler processes delivery receipts cleanly."""
        ack = ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=uuid4(),
        )
        await handle_chat_ack(
            ctx=mock_context,  # type: ignore
            sender=test_sender,
            msg=ack,
        )
        mock_context.logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_session_start_end_protocol_flow(
        self,
        mock_context: MockContext,
        test_sender: str,
        message_service: MessageService,
    ) -> None:
        """Verify full conversational cycle from start to end over Chat Protocol."""
        setup_chat_protocol(message_service=message_service)

        # 1. Start Session
        start_msg = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[StartSessionContent(type="start-session")],
        )
        await handle_chat_message(
            ctx=mock_context,  # type: ignore
            sender=test_sender,
            msg=start_msg,
        )
        assert len(mock_context.sent_messages) == 2
        _, start_reply = mock_context.sent_messages[1]
        assert "Session initialized" in start_reply.content[0].text

        mock_context.sent_messages.clear()

        # 2. Conversational Message
        turn_msg = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text="ping")],
        )
        await handle_chat_message(
            ctx=mock_context,  # type: ignore
            sender=test_sender,
            msg=turn_msg,
        )
        assert len(mock_context.sent_messages) == 2
        _, turn_reply = mock_context.sent_messages[1]
        assert "Pong!" in turn_reply.content[0].text

        mock_context.sent_messages.clear()

        # 3. End Session
        end_msg = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[EndSessionContent(type="end-session")],
        )
        await handle_chat_message(
            ctx=mock_context,  # type: ignore
            sender=test_sender,
            msg=end_msg,
        )
        assert len(mock_context.sent_messages) == 2
        _, end_reply = mock_context.sent_messages[1]
        types = [b.type for b in end_reply.content]
        assert "end-session" in types
