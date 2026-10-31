"""
Unit Tests for Specialized Agents: Planner, Research, Execution, and Verification.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agents.execution_agent import ExecutionAgent
from agents.planner_agent import PlannerAgent
from agents.research_agent import ResearchAgent
from agents.verification_agent import VerificationAgent
from tools.api_tools import register_api_tools
from tools.execution_tools import register_execution_tools
from tools.tool_registry import ToolRegistry


@pytest.fixture
def test_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_api_tools(registry)
    register_execution_tools(registry)
    return registry


class TestSpecializedAgents:
    """Tests verifying distinct responsibilities of each specialized agent."""

    @pytest.mark.asyncio
    async def test_planner_agent_creates_subtasks(self, test_tool_registry: ToolRegistry) -> None:
        mock_asi = MagicMock()
        mock_asi.plan_task = AsyncMock(
            return_value={
                "intent": "token_valuation",
                "subtasks": [
                    {"id": 1, "agent": "research", "action": "fetch_token_price", "params": {"token_id": "fetch-ai"}},
                    {"id": 2, "agent": "verification", "action": "verify", "params": {}},
                ],
            }
        )
        planner = PlannerAgent(asi_client=mock_asi, tool_registry=test_tool_registry)
        plan = await planner.create_plan(
            task_id=str(uuid4()),
            user_request="Get the current price of Fetch.ai",
        )
        assert plan["intent"] == "token_valuation"
        assert len(plan["subtasks"]) == 2
        assert plan["subtasks"][0]["agent"] == "research"

    @pytest.mark.asyncio
    async def test_research_agent_executes_query(self, test_tool_registry: ToolRegistry) -> None:
        research = ResearchAgent(tool_registry=test_tool_registry)
        result = await research.execute_research(
            task_id=str(uuid4()),
            tool_name="fetch_token_price",
            params={"token_id": "fetch-ai"},
        )
        assert result["success"] is True
        assert result["data"]["asset"] == "fetch-ai"

    @pytest.mark.asyncio
    async def test_execution_agent_performs_calculation(self, test_tool_registry: ToolRegistry) -> None:
        execution = ExecutionAgent(tool_registry=test_tool_registry)
        result = await execution.execute_task(
            task_id=str(uuid4()),
            tool_name="calculate_expression",
            params={"expression": "250 * 4"},
        )
        assert result["success"] is True
        assert result["data"]["result"] == 1000

    @pytest.mark.asyncio
    async def test_verification_agent_detects_failure(self) -> None:
        mock_asi = MagicMock()
        mock_asi.verify_outcome = AsyncMock(
            return_value={"is_valid": False, "quality_score": 0.2, "needs_retry": True, "reasoning": "Missing price"}
        )
        verifier = VerificationAgent(asi_client=mock_asi)

        verdict = await verifier.verify_results(
            task_id=str(uuid4()),
            goal="Get price",
            plan=[],
            results=[{"success": False, "error": "Timeout"}],
        )
        assert verdict["is_valid"] is False
        assert verdict["needs_retry"] is True
