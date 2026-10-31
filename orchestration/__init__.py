"""
Orchestration Package for Stranger Builds 2026.
Contains LangGraph state definitions, ASI-1 client, workflow graph, and orchestration engine.
"""

from .asi_client import ASI1Client
from .state import WorkflowState


def get_workflow_builder(*args, **kwargs):
    from .workflow import MultiAgentWorkflowBuilder
    return MultiAgentWorkflowBuilder(*args, **kwargs)


def get_orchestration_engine():
    """Lazily import and retrieve the global orchestration engine."""
    from .engine import get_orchestration_engine as _get_engine
    return _get_engine()


__all__ = [
    "ASI1Client",
    "WorkflowState",
    "get_workflow_builder",
    "get_orchestration_engine",
]
