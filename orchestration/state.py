"""
Typed State Definitions for LangGraph Multi-Agent Orchestration.
"""

from typing import Annotated, Any, TypedDict
from langgraph.graph.message import add_messages


class WorkflowState(TypedDict, total=False):
    """
    Shared workflow state passed across all nodes in the LangGraph execution graph.
    """

    task_id: str
    session_id: str
    sender: str
    user_request: str
    intent: str | None
    plan: list[dict[str, Any]]
    current_subtask_index: int
    results: list[dict[str, Any]]
    verification: dict[str, Any]
    final_response: str | None
    retry_count: int
    max_retries: int
    error: str | None
    status: str
