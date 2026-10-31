"""
Session Management Service for Fetch.ai Autonomous Agent.
Tracks active conversation sessions, boundary events, and request context.
"""

from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any
from uuid import UUID, uuid4

from core.exceptions import SessionClosedError, SessionNotFoundError
from core.logger import get_agent_logger

logger = get_agent_logger("services.session_service")


class SessionStatus(str, Enum):
    """Lifecycle status of a dialogue session."""

    ACTIVE = "active"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class SessionState:
    """
    State container for an active multi-turn agent conversation session.
    """

    def __init__(
        self,
        session_id: UUID,
        sender: str,
        created_at: datetime | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.session_id: UUID = session_id
        self.sender: str = sender
        self.status: SessionStatus = SessionStatus.ACTIVE
        self.created_at: datetime = created_at or now
        self.last_activity: datetime = now
        self.context_memory: dict[str, Any] = {}
        self.message_history: list[dict[str, Any]] = []

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    def record_interaction(
        self,
        msg_id: UUID,
        direction: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append an interaction entry to the session history."""
        self.touch()
        self.message_history.append(
            {
                "msg_id": str(msg_id),
                "direction": direction,
                "summary": summary,
                "timestamp": self.last_activity.isoformat(),
                "metadata": metadata or {},
            }
        )

    def set_context(self, key: str, value: Any) -> None:
        """Store context variable for subsequent turns."""
        self.touch()
        self.context_memory[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a stored context variable."""
        return self.context_memory.get(key, default)

    def terminate(self) -> None:
        """Mark session as ended."""
        self.touch()
        self.status = SessionStatus.TERMINATED

    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status == SessionStatus.ACTIVE


class SessionService:
    """
    Thread-safe in-memory session registry and lifecycle manager.
    Designed to easily interface with distributed stores (Redis/Postgres) in Phase 2.
    """

    def __init__(self, expiry_seconds: int = 86400) -> None:
        self._sessions: dict[UUID, SessionState] = {}
        self._sender_active_session: dict[str, UUID] = {}
        self._expiry_seconds: int = expiry_seconds
        self._lock: Lock = Lock()

    def start_session(
        self,
        sender: str,
        custom_session_id: UUID | None = None,
    ) -> SessionState:
        """
        Explicitly initiate a new session for a given sender.
        Closes any previously active session for that sender.
        """
        with self._lock:
            # Terminate existing active session if one exists
            existing_session_id = self._sender_active_session.get(sender)
            if existing_session_id and existing_session_id in self._sessions:
                old_session = self._sessions[existing_session_id]
                if old_session.is_active():
                    logger.info(f"Closing previous active session {existing_session_id} for sender {sender}")
                    old_session.terminate()

            session_id = custom_session_id or uuid4()
            session = SessionState(session_id=session_id, sender=sender)
            self._sessions[session_id] = session
            self._sender_active_session[sender] = session_id
            logger.info(f"Started new session {session_id} for sender {sender}")
            return session

    def get_or_create_session(
        self,
        sender: str,
    ) -> SessionState:
        """
        Retrieve current active session for sender or automatically provision one.
        """
        with self._lock:
            self._prune_expired_sessions_unlocked()
            active_id = self._sender_active_session.get(sender)
            if active_id and active_id in self._sessions:
                session = self._sessions[active_id]
                if session.is_active():
                    session.touch()
                    return session

            # Create default implicit session
            session_id = uuid4()
            session = SessionState(session_id=session_id, sender=sender)
            self._sessions[session_id] = session
            self._sender_active_session[sender] = session_id
            logger.info(f"Provisioned implicit session {session_id} for sender {sender}")
            return session

    def get_session(self, session_id: UUID) -> SessionState:
        """
        Fetch a session by its unique identifier.
        """
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFoundError(f"Session with ID {session_id} does not exist.")
            return self._sessions[session_id]

    def get_active_session_for_sender(self, sender: str) -> SessionState | None:
        """
        Fetch active session for sender, if any.
        """
        with self._lock:
            active_id = self._sender_active_session.get(sender)
            if active_id and active_id in self._sessions:
                session = self._sessions[active_id]
                if session.is_active():
                    return session
            return None

    def end_session(self, sender: str) -> SessionState | None:
        """
        Terminate the active session for a sender.
        """
        with self._lock:
            active_id = self._sender_active_session.get(sender)
            if not active_id or active_id not in self._sessions:
                logger.warning(f"No active session found to end for sender {sender}")
                return None

            session = self._sessions[active_id]
            session.terminate()
            self._sender_active_session.pop(sender, None)
            logger.info(f"Ended session {active_id} for sender {sender}")
            return session

    def record_message(
        self,
        sender: str,
        msg_id: UUID,
        direction: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Record interaction on the sender's active session.
        """
        with self._lock:
            active_id = self._sender_active_session.get(sender)
            if active_id and active_id in self._sessions:
                self._sessions[active_id].record_interaction(
                    msg_id=msg_id,
                    direction=direction,
                    summary=summary,
                    metadata=metadata,
                )

    def _prune_expired_sessions_unlocked(self) -> None:
        """Prune idle sessions beyond expiry threshold."""
        now = datetime.now(timezone.utc)
        expired_ids = []
        for s_id, session in self._sessions.items():
            if session.is_active():
                delta = (now - session.last_activity).total_seconds()
                if delta > self._expiry_seconds:
                    session.status = SessionStatus.EXPIRED
                    expired_ids.append((s_id, session.sender))

        for s_id, sender in expired_ids:
            logger.info(f"Session {s_id} for sender {sender} expired due to inactivity")
            if self._sender_active_session.get(sender) == s_id:
                self._sender_active_session.pop(sender, None)

    def get_active_session_count(self) -> int:
        """Return total count of currently active sessions."""
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.is_active())
