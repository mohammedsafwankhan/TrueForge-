"""
SQLAlchemy ORM Models for Task History, Agent Activity, Workflows, and Executions.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base model for all database tables."""


class TaskHistory(Base):
    """
    Persistent log of all high-level tasks initiated by users or remote agents.
    """

    __tablename__ = "task_history"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    sender: Mapped[str] = mapped_column(String(128), index=True)
    user_request: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, in_progress, completed, failed
    plan_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentActivity(Base):
    """
    Detailed audit log of specialized agent operations (Planner, Research, Execution, Verification).
    """

    __tablename__ = "agent_activity"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="success")  # success, failure, retried
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class WorkflowRecord(Base):
    """
    Checkpoint and state record for LangGraph execution workflows.
    """

    __tablename__ = "workflow_records"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    current_step: Mapped[str] = mapped_column(String(64))
    state_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ExecutionLog(Base):
    """
    Record of individual tool invocations (APIs, mathematical evaluations, MCP tools).
    """

    __tablename__ = "execution_records"

    execution_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(64), index=True)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TransactionRef(Base):
    """
    Ledger transaction and settlement references for Phase 2 operations and Phase 3 payment protocol.
    """

    __tablename__ = "transaction_references"

    tx_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sender_wallet: Mapped[str] = mapped_column(String(128))
    recipient_wallet: Mapped[str] = mapped_column(String(128))
    amount: Mapped[str] = mapped_column(String(64))
    denom: Mapped[str] = mapped_column(String(32), default="afet")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, confirmed, failed
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
