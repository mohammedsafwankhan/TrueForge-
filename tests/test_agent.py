"""
Unit and Integration Tests for Primary Agent and Session Management.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from uagents import Agent

from agents.primary_agent import create_primary_agent, get_agent_details
from core.config import Settings
from core.exceptions import SessionNotFoundError
from services.session_service import SessionService, SessionStatus


class TestAgentInitialization:
    """Tests verifying primary agent initialization and cryptographic address properties."""

    def test_agent_initialization_with_seed(self) -> None:
        """Verify agent generates a deterministic address from seed and includes chat protocol."""
        seed = "test_stranger_builds_agent_deterministic_seed_phase1"
        settings = Settings(
            AGENT_NAME="stranger_builds_primary_agent",
            AGENT_SEED=seed,
            AGENT_PORT=8001,
            AGENT_NETWORK="mainnet",
        )

        agent = create_primary_agent(settings=settings)

        assert agent.name == "stranger_builds_primary_agent"
        assert agent.address.startswith("agent1")
        assert agent.wallet is not None
        wallet_address = str(agent.wallet.address()) if callable(agent.wallet.address) else str(agent.wallet.address)
        assert wallet_address.startswith("fetch1")

        # Verify chat protocol inclusion
        assert len(agent.protocols) >= 1
        assert any(p.name == "AgentChatProtocol" for p in agent.protocols.values())
        protocol_digests = list(agent.protocols.keys())
        assert any(d.startswith("proto:") for d in protocol_digests)

    def test_deterministic_address_consistency(self) -> None:
        """Verify identical seed generates identical cryptographic agent address."""
        seed = "constant_seed_for_reproducibility_check_998877"
        settings = Settings(AGENT_SEED=seed)

        agent_1 = create_primary_agent(settings=settings)
        agent_2 = create_primary_agent(settings=settings)

        assert agent_1.address == agent_2.address
        addr1 = str(agent_1.wallet.address()) if callable(agent_1.wallet.address) else str(agent_1.wallet.address)
        addr2 = str(agent_2.wallet.address()) if callable(agent_2.wallet.address) else str(agent_2.wallet.address)
        assert addr1 == addr2

    def test_get_agent_details(self) -> None:
        """Verify get_agent_details extracts correct diagnostics."""
        settings = Settings(AGENT_SEED="diagnostic_test_seed_112233")
        agent = create_primary_agent(settings=settings)
        details = get_agent_details(agent)

        assert details["name"] == agent.name
        assert details["address"] == agent.address
        expected_wallet = str(agent.wallet.address()) if callable(agent.wallet.address) else str(agent.wallet.address)
        assert details["wallet_address"] == expected_wallet
        assert isinstance(details["protocols"], list)
        assert details["metadata"]["hackathon"] == "Stranger Builds 2026"


class TestSessionService:
    """Tests verifying session lifecycle, context persistence, and expiry."""

    def test_start_session_creates_active_session(
        self,
        session_service: SessionService,
        test_sender: str,
    ) -> None:
        """Verify starting session creates active state and assigns unique ID."""
        session = session_service.start_session(test_sender)
        assert session.is_active()
        assert session.sender == test_sender
        assert session_service.get_active_session_count() == 1

        fetched = session_service.get_session(session.session_id)
        assert fetched.session_id == session.session_id

    def test_start_session_terminates_previous_active_session(
        self,
        session_service: SessionService,
        test_sender: str,
    ) -> None:
        """Verify starting a new session closes any previous active session for that sender."""
        first_session = session_service.start_session(test_sender)
        first_id = first_session.session_id
        assert first_session.is_active()

        second_session = session_service.start_session(test_sender)
        assert second_session.is_active()
        assert second_session.session_id != first_id

        # First session must now be terminated
        old = session_service.get_session(first_id)
        assert old.status == SessionStatus.TERMINATED

    def test_end_session(
        self,
        session_service: SessionService,
        test_sender: str,
    ) -> None:
        """Verify ending session transitions state to TERMINATED and updates active counter."""
        session = session_service.start_session(test_sender)
        assert session_service.get_active_session_count() == 1

        ended = session_service.end_session(test_sender)
        assert ended is not None
        assert ended.status == SessionStatus.TERMINATED
        assert session_service.get_active_session_count() == 0

    def test_context_memory_persistence(
        self,
        session_service: SessionService,
        test_sender: str,
    ) -> None:
        """Verify arbitrary context variables persist across turns in the session."""
        session = session_service.start_session(test_sender)
        session.set_context("preferred_currency", "FET")
        session.set_context("risk_tolerance", "moderate")

        retrieved = session_service.get_or_create_session(test_sender)
        assert retrieved.get_context("preferred_currency") == "FET"
        assert retrieved.get_context("risk_tolerance") == "moderate"

    def test_session_expiry_pruning(
        self,
        test_sender: str,
    ) -> None:
        """Verify idle sessions beyond threshold are expired upon prune check."""
        short_lived_service = SessionService(expiry_seconds=1)
        session = short_lived_service.start_session(test_sender)

        # Manually backdate last_activity
        session.last_activity = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Calling get_or_create_session triggers prune
        new_session = short_lived_service.get_or_create_session(test_sender)
        assert new_session.session_id != session.session_id

        # Old session should be marked EXPIRED
        old_session = short_lived_service.get_session(session.session_id)
        assert old_session.status == SessionStatus.EXPIRED

    def test_get_nonexistent_session_raises(
        self,
        session_service: SessionService,
    ) -> None:
        """Verify SessionNotFoundError is raised for unknown session ID."""
        with pytest.raises(SessionNotFoundError):
            session_service.get_session(uuid4())
