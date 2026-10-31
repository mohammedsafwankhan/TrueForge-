"""
Pytest Fixtures for Stranger Builds 2026 Agent Test Suite.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
)

from services.message_service import MessageService
from services.session_service import SessionService


class MockContext:
    """Mock Fetch.ai agent execution context."""

    def __init__(self, agent_address: str = "agent1q_test_mock_address") -> None:
        self.address = agent_address
        self.logger = MagicMock()
        self.send = AsyncMock()
        self.sent_messages: list[tuple[str, Any]] = []

        async def _record_send(destination: str, message: Any) -> None:
            self.sent_messages.append((destination, message))

        self.send.side_effect = _record_send


@pytest.fixture
def mock_context() -> MockContext:
    """Fixture providing a mock Context tracking outgoing sends."""
    return MockContext()


@pytest.fixture
def test_sender() -> str:
    """Fixture providing a mock sender agent address."""
    return "agent1q_test_remote_sender_address_xyz123"


@pytest.fixture
def session_service() -> SessionService:
    """Fixture providing an isolated SessionService instance."""
    return SessionService(expiry_seconds=3600)


@pytest.fixture
def message_service(session_service: SessionService) -> MessageService:
    """Fixture providing an isolated MessageService instance."""
    return MessageService(
        session_service=session_service,
        dedup_cache_size=1000,
        dedup_ttl_seconds=3600,
    )


@pytest.fixture
def sample_text_message() -> ChatMessage:
    """Fixture generating a standard single-text ChatMessage."""
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text="Hello from Stranger Builds Hackathon!")],
    )


@pytest.fixture
def sample_start_session_message() -> ChatMessage:
    """Fixture generating a session start ChatMessage."""
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[
            StartSessionContent(type="start-session"),
            TextContent(type="text", text="Initiate autonomous agent session"),
        ],
    )


@pytest.fixture
def sample_end_session_message() -> ChatMessage:
    """Fixture generating a session termination ChatMessage."""
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[
            EndSessionContent(type="end-session"),
            TextContent(type="text", text="Closing session"),
        ],
    )


@pytest.fixture
def sample_multi_text_message() -> ChatMessage:
    """Fixture generating a message with multiple TextContent blocks."""
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text="Part 1: Initial telemetry header"),
            TextContent(type="text", text="Part 2: Primary payload query"),
            TextContent(type="text", text="Part 3: Closing constraint flag"),
        ],
    )
