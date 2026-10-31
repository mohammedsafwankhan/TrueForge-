"""
Unit Tests for Chat Protocol Message Models and Inbound Validation.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
)

from core.exceptions import InvalidMessageError
from models.requests import SessionAction
from services.message_service import MessageService
from services.session_service import SessionService


class TestChatMessageModels:
    """Tests covering official Chat Protocol data models."""

    def test_chat_message_instantiation_valid(self) -> None:
        """Verify ChatMessage instantiates correctly with timezone-aware datetime."""
        now = datetime.now(timezone.utc)
        msg_id = uuid4()
        msg = ChatMessage(
            timestamp=now,
            msg_id=msg_id,
            content=[TextContent(type="text", text="Test message")],
        )
        assert msg.msg_id == msg_id
        assert msg.timestamp == now
        assert msg.timestamp.tzinfo is not None
        assert len(msg.content) == 1
        assert isinstance(msg.content[0], TextContent)
        assert msg.content[0].text == "Test message"

    def test_chat_acknowledgement_instantiation(self) -> None:
        """Verify ChatAcknowledgement instantiates with target msg_id."""
        now = datetime.now(timezone.utc)
        target_id = uuid4()
        ack = ChatAcknowledgement(
            timestamp=now,
            acknowledged_msg_id=target_id,
            metadata={"status": "received"},
        )
        assert ack.acknowledged_msg_id == target_id
        assert ack.timestamp == now
        assert ack.metadata == {"status": "received"}

    def test_start_session_content_model(self) -> None:
        """Verify StartSessionContent structure and type literal."""
        start = StartSessionContent(type="start-session")
        assert start.type == "start-session"

    def test_end_session_content_model(self) -> None:
        """Verify EndSessionContent structure and type literal."""
        end = EndSessionContent(type="end-session")
        assert end.type == "end-session"

    def test_multiple_text_content_blocks(self) -> None:
        """Verify ChatMessage holding multiple sequential TextContent blocks."""
        msg = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text="Block Alpha"),
                TextContent(type="text", text="Block Beta"),
                TextContent(type="text", text="Block Gamma"),
            ],
        )
        assert len(msg.content) == 3
        texts = [b.text for b in msg.content if isinstance(b, TextContent)]
        assert texts == ["Block Alpha", "Block Beta", "Block Gamma"]


class TestMessageServiceParsingAndValidation:
    """Tests covering message validation, extraction, and edge cases."""

    def test_parse_valid_text_message(
        self,
        message_service: MessageService,
        test_sender: str,
        sample_text_message: ChatMessage,
    ) -> None:
        """Verify standard text message extracts cleanly."""
        ctx = message_service.parse_inbound_message(test_sender, sample_text_message)
        assert ctx.sender == test_sender
        assert ctx.msg_id == sample_text_message.msg_id
        assert ctx.session_action == SessionAction.NONE
        assert ctx.extracted_text == ["Hello from Stranger Builds Hackathon!"]
        assert ctx.combined_text == "Hello from Stranger Builds Hackathon!"

    def test_parse_start_session_message(
        self,
        message_service: MessageService,
        test_sender: str,
        sample_start_session_message: ChatMessage,
    ) -> None:
        """Verify StartSessionContent triggers SessionAction.START."""
        ctx = message_service.parse_inbound_message(test_sender, sample_start_session_message)
        assert ctx.session_action == SessionAction.START
        assert "Initiate autonomous agent session" in ctx.extracted_text

    def test_parse_end_session_message(
        self,
        message_service: MessageService,
        test_sender: str,
        sample_end_session_message: ChatMessage,
    ) -> None:
        """Verify EndSessionContent triggers SessionAction.END."""
        ctx = message_service.parse_inbound_message(test_sender, sample_end_session_message)
        assert ctx.session_action == SessionAction.END

    def test_parse_multi_text_blocks(
        self,
        message_service: MessageService,
        test_sender: str,
        sample_multi_text_message: ChatMessage,
    ) -> None:
        """Verify multiple text blocks are combined and ordered properly."""
        ctx = message_service.parse_inbound_message(test_sender, sample_multi_text_message)
        assert len(ctx.extracted_text) == 3
        assert "Part 1" in ctx.combined_text
        assert "Part 2" in ctx.combined_text
        assert "Part 3" in ctx.combined_text

    def test_parse_missing_msg_id_raises_error(
        self,
        message_service: MessageService,
        test_sender: str,
    ) -> None:
        """Verify an error is raised when msg_id is missing or None."""
        class MalformedMessage:
            timestamp = datetime.now(timezone.utc)
            msg_id = None
            content = [TextContent(type="text", text="broken")]

        with pytest.raises(InvalidMessageError) as exc_info:
            message_service.parse_inbound_message(test_sender, MalformedMessage())  # type: ignore
        assert "missing required 'msg_id'" in str(exc_info.value).lower()

    def test_parse_missing_content_raises_error(
        self,
        message_service: MessageService,
        test_sender: str,
    ) -> None:
        """Verify error is raised when content is not a list."""
        class MalformedContentMessage:
            timestamp = datetime.now(timezone.utc)
            msg_id = uuid4()
            content = "not a list"

        with pytest.raises(InvalidMessageError) as exc_info:
            message_service.parse_inbound_message(test_sender, MalformedContentMessage())  # type: ignore
        assert "must be a valid list" in str(exc_info.value).lower()

    def test_parse_none_message_raises_error(
        self,
        message_service: MessageService,
        test_sender: str,
    ) -> None:
        """Verify error is raised on null message."""
        with pytest.raises(InvalidMessageError):
            message_service.parse_inbound_message(test_sender, None)  # type: ignore

    def test_timezone_normalization(
        self,
        message_service: MessageService,
        test_sender: str,
    ) -> None:
        """Verify naive datetime is normalized to timezone-aware UTC."""
        naive_now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive datetime
        class NaiveTimestampMsg:
            timestamp = naive_now
            msg_id = uuid4()
            content = [TextContent(type="text", text="timezone test")]

        ctx = message_service.parse_inbound_message(test_sender, NaiveTimestampMsg())  # type: ignore
        assert ctx.timestamp.tzinfo is not None
        assert ctx.timestamp.tzinfo == timezone.utc
