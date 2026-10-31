"""
Database and Caching Package for Stranger Builds 2026.
"""

from .cache import DistributedCache, cache_service
from .connection import (
    get_db_session,
    get_engine,
    log_agent_activity,
    log_tool_execution,
    record_task_history,
    update_task_completion,
)
from .models import AgentActivity, Base, ExecutionLog, TaskHistory, TransactionRef, WorkflowRecord

__all__ = [
    "Base",
    "TaskHistory",
    "AgentActivity",
    "WorkflowRecord",
    "ExecutionLog",
    "TransactionRef",
    "get_engine",
    "get_db_session",
    "record_task_history",
    "update_task_completion",
    "log_agent_activity",
    "log_tool_execution",
    "DistributedCache",
    "cache_service",
]
