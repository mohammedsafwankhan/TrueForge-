"""
Unit Tests for LangGraph StateGraph Multi-Agent Orchestration.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agents.execution_agent import ExecutionAgent
from agents.planner_agent import PlannerAgent
from agents.research_agent import ResearchAgent
from agents.verification_agent import VerificationAgent
from orchestration.workflow import MultiAgentWorkflowBuilder
from tools.api_tools import register_api_tools
from tools.execution_tools import register_execution_tools
from tools.tool_registry import ToolRegistry


@pytest.fixture
def workflow_setup():
    registry = ToolRegistry()
    register_api_tools(registry)
    register_execution_tools(registry)

    mock_asi = MagicMock()
    mock_asi.plan_task = AsyncMock(
        return_value={
            "intent": "calculation_and_query",
            "subtasks": [
                {
                    "id": 1,
                    "agent": "execution",
                    "action": "calculate_expression",
                    "tool": "calculate_expression",
                    "params": {"expression": "50 * 2"},
                },
                {
                    "id": 2,
                    "agent": "verification",
                    "action": "verify",
                    "tool": None,
                    "params": {},
                },
            ],
        }
    )
    mock_asi.verify_outcome = AsyncMock(
        return_value={
            "is_valid": True,
            "quality_score": 0.95,
            "reasoning": "Calculation verified accurately",
            "needs_retry": False,
        }
    )
    mock_asi.synthesize_final_response = AsyncMock(
        return_value="Computation complete: 50 * 2 = 100."
    )

    planner = PlannerAgent(asi_client=mock_asi, tool_registry=registry)
    research = ResearchAgent(tool_registry=registry)
    execution = ExecutionAgent(tool_registry=registry)
    verifier = VerificationAgent(asi_client=mock_asi)

    builder = MultiAgentWorkflowBuilder(
        planner_agent=planner,
        research_agent=research,
        execution_agent=execution,
        verification_agent=verifier,
        asi_client=mock_asi,
        tool_registry=registry,
    )
    graph = builder.build_graph()
    return graph, mock_asi


class TestLangGraphWorkflow:
    """Tests covering LangGraph graph execution, checkpointing, and conditional routing."""

    @pytest.mark.asyncio
    async def test_full_workflow_execution(self, workflow_setup) -> None:
        graph, _ = workflow_setup
        task_id = str(uuid4())

        initial_state = {
            "task_id": task_id,
            "session_id": "test_session_1",
            "sender": "agent1q_test_sender",
            "user_request": "Calculate 50 times 2",
            "intent": None,
            "plan": [],
            "current_subtask_index": 0,
            "results": [],
            "verification": {},
            "final_response": None,
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
            "status": "started",
        }

        config = {"configurable": {"thread_id": task_id}}
        final_state = await graph.ainvoke(initial_state, config=config)

        assert final_state["status"] == "completed"
        assert len(final_state["results"]) >= 1
        assert final_state["verification"]["is_valid"] is True
        assert "100" in final_state["final_response"]

    @pytest.mark.asyncio
    async def test_workflow_retry_on_verification_failure(self, workflow_setup) -> None:
        graph, mock_asi = workflow_setup
        # First verification fails, second succeeds
        mock_asi.verify_outcome = AsyncMock(
            side_effect=[
                {"is_valid": False, "quality_score": 0.1, "reasoning": "First run simulated failure", "needs_retry": True},
                {"is_valid": True, "quality_score": 0.9, "reasoning": "Second run verified", "needs_retry": False},
            ]
        )

        task_id = str(uuid4())
        initial_state = {
            "task_id": task_id,
            "session_id": "test_session_retry",
            "sender": "agent1q_test_sender",
            "user_request": "Calculate 50 times 2",
            "intent": None,
            "plan": [],
            "current_subtask_index": 0,
            "results": [],
            "verification": {},
            "final_response": None,
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
            "status": "started",
        }

        config = {"configurable": {"thread_id": task_id}}
        final_state = await graph.ainvoke(initial_state, config=config)

        assert final_state["status"] == "completed"
        assert final_state["retry_count"] >= 1
