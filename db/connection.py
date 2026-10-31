"""
Asynchronous Database Connection and Repository Layer.
Supports PostgreSQL (asyncpg) with automatic seamless local SQLite fallback.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings
from core.logger import get_agent_logger
from db.models import AgentActivity, Base, ExecutionLog, TaskHistory, WorkflowRecord

logger = get_agent_logger("db.connection")

_engine = None
_session_maker = None


async def get_engine():
    """Retrieve or lazily initialize the async database engine."""
    global _engine, _session_maker
    if _engine is not None:
        return _engine

    cfg = get_settings()
    db_url = cfg.POSTGRES_URL

    # Try connecting to PostgreSQL if configured
    if db_url and "postgresql" in db_url:
        try:
            test_engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
            async with test_engine.connect() as conn:
                await conn.execute(select(1))
            logger.info("Successfully established connection to PostgreSQL database.")
            _engine = test_engine
        except Exception as exc:
            logger.warning(
                f"PostgreSQL connection to {db_url} unreachable ({exc}). Falling back to local SQLite engine."
            )
            _engine = None

    if _engine is None:
        # Fallback to local async SQLite
        sqlite_url = "sqlite+aiosqlite:///stranger_builds.db"
        logger.info(f"Using SQLite database engine at {sqlite_url}")
        _engine = create_async_engine(sqlite_url, echo=False)

    _session_maker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)

    # Initialize tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return _engine


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional asynchronous database session."""
    global _session_maker
    if _session_maker is None:
        await get_engine()
    assert _session_maker is not None
    async with _session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def record_task_history(
    task_id: str,
    session_id: str,
    sender: str,
    user_request: str,
    intent: str | None = None,
    plan_data: dict[str, Any] | None = None,
    status: str = "in_progress",
) -> None:
    """Record or update task history entry."""
    try:
        async with get_db_session() as session:
            task = TaskHistory(
                id=task_id,
                session_id=session_id,
                sender=sender,
                user_request=user_request,
                intent=intent,
                status=status,
                plan_data=plan_data,
            )
            session.add(task)
    except Exception as exc:
        logger.warning(f"Could not write task history to DB: {exc}")


async def update_task_completion(
    task_id: str,
    final_response: str,
    verification_passed: bool,
    status: str = "completed",
) -> None:
    """Update task completion status and verified response."""
    try:
        async with get_db_session() as session:
            stmt = select(TaskHistory).where(TaskHistory.id == task_id)
            res = await session.execute(stmt)
            task = res.scalar_one_or_none()
            if task:
                task.final_response = final_response
                task.verification_passed = verification_passed
                task.status = status
                task.completed_at = datetime.now(timezone.utc)
    except Exception as exc:
        logger.warning(f"Could not update task completion: {exc}")


async def log_agent_activity(
    task_id: str,
    agent_name: str,
    action: str,
    status: str = "success",
    details: dict[str, Any] | None = None,
    duration_ms: float = 0.0,
) -> None:
    """Log specialized agent operation for observability and debugging."""
    try:
        async with get_db_session() as session:
            activity = AgentActivity(
                task_id=task_id,
                agent_name=agent_name,
                action=action,
                status=status,
                details=details,
                duration_ms=duration_ms,
            )
            session.add(activity)
    except Exception as exc:
        logger.warning(f"Could not log agent activity: {exc}")


async def log_tool_execution(
    tool_name: str,
    parameters: dict[str, Any] | None = None,
    result_data: dict[str, Any] | None = None,
    error_message: str | None = None,
    success: bool = True,
    duration_ms: float = 0.0,
    task_id: str | None = None,
) -> None:
    """Log individual tool execution record."""
    try:
        async with get_db_session() as session:
            log = ExecutionLog(
                task_id=task_id,
                tool_name=tool_name,
                parameters=parameters,
                result_data=result_data,
                error_message=error_message,
                success=success,
                duration_ms=duration_ms,
            )
            session.add(log)
    except Exception as exc:
        logger.warning(f"Could not log tool execution: {exc}")
