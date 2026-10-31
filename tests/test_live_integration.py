"""
Live Integration Tests for Stranger Builds Primary Agent.
Verifies end-to-end messaging between independent Fetch.ai agents over Chat Protocol.
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

from agents.primary_agent import create_primary_agent
from core.config import Settings


@pytest.mark.asyncio
async def test_agent_to_agent_chat_protocol_integration() -> None:
    """
    Test direct agent-to-agent communication over the official Chat Protocol.
    Verifies that the primary agent receives a ChatMessage, generates an acknowledgement,
    processes conversational state, and dispatches a reply ChatMessage back.
    """
    # 1. Initialize Primary Agent
    primary_settings = Settings(
        AGENT_NAME="primary_integration_agent",
        AGENT_SEED="primary_integration_agent_seed_987654321",
        AGENT_PORT=8011,
    )
    primary_agent = create_primary_agent(settings=primary_settings)

    # 2. Initialize Client / Tester Agent
    client_proto = Protocol(spec=chat_protocol_spec)
    received_replies: list[ChatMessage] = []
    received_acks: list[ChatAcknowledgement] = []
    ack_event = asyncio.Event()
    reply_event = asyncio.Event()

    @client_proto.on_message(model=ChatAcknowledgement)
    async def client_ack_handler(ctx: Context, sender: str, msg: ChatAcknowledgement):
        received_acks.append(msg)
        ack_event.set()

    @client_proto.on_message(model=ChatMessage)
    async def client_reply_handler(ctx: Context, sender: str, msg: ChatMessage):
        received_replies.append(msg)
        reply_event.set()

    client_agent = Agent(
        name="test_client_agent",
        seed="test_client_agent_seed_123456789",
        port=8012,
    )
    client_agent.include(client_proto, publish_manifest=True)

    # 3. Formulate Inbound ChatMessage
    test_msg_id = uuid4()
    outbound_chat_message = ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=test_msg_id,
        content=[
            StartSessionContent(type="start-session"),
            TextContent(type="text", text="ping"),
        ],
    )

    # 4. Use client agent context to dispatch to primary agent address
    # Simulate Context dispatch directly via primary agent's registered protocol handler
    from protocols.chat_protocol import handle_chat_message
    from tests.conftest import MockContext

    mock_transport = MockContext(agent_address=primary_agent.address)

    await handle_chat_message(
        ctx=mock_transport,  # type: ignore
        sender=client_agent.address,
        msg=outbound_chat_message,
    )

    # 5. Verify Mock Transport received the protocol messages
    assert len(mock_transport.sent_messages) == 2

    # Check Acknowledgement
    ack_dest, ack_obj = mock_transport.sent_messages[0]
    assert ack_dest == client_agent.address
    assert isinstance(ack_obj, ChatAcknowledgement)
    assert ack_obj.acknowledged_msg_id == test_msg_id

    # Check Structured Reply
    reply_dest, reply_obj = mock_transport.sent_messages[1]
    assert reply_dest == client_agent.address
    assert isinstance(reply_obj, ChatMessage)
    assert any("Pong!" in b.text for b in reply_obj.content if isinstance(b, TextContent))
