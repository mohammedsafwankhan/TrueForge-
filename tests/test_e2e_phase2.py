"""
Live End-to-End Integration Tests for Phase 2 Autonomous Multi-Agent Pipeline.
Verifies real ASI-1 reasoning, tool execution, result verification, and database auditing.
"""

from uuid import uuid4
import pytest
from sqlalchemy import select

from db.connection import get_db_session
from db.models import AgentActivity, TaskHistory
from orchestration.engine import MultiAgentEngine


class TestPhase2EndToEnd:
    """Live end-to-end multi-agent execution pipeline tests."""

    @pytest.mark.asyncio
    async def test_live_autonomous_task_execution_pipeline(self) -> None:
        """
        Execute an end-to-end autonomous multi-agent pipeline using live ASI-1
        and the real CoinGecko pricing oracle for Fetch.ai.
        """
        engine = MultiAgentEngine()
        task_id = str(uuid4())
        session_id = f"session_e2e_{uuid4()}"
        sender = "agent1q_test_e2e_requester"

        user_request = "What is the live price of fetch-ai ($FET)?"

        final_state = await engine.execute_task(
            user_request=user_request,
            session_id=session_id,
            sender=sender,
            task_id=task_id,
        )

        # 1. State Verification
        assert final_state["status"] == "completed"
        assert final_state["task_id"] == task_id
        assert len(final_state["plan"]) >= 1
        assert len(final_state["results"]) >= 1
        assert final_state["verification"].get("is_valid") is True
        assert final_state["final_response"] is not None
        assert len(final_state["final_response"]) > 0

        # 2. Database Audit Verification
        async with get_db_session() as session:
            stmt = select(TaskHistory).where(TaskHistory.id == task_id)
            task_rec = (await session.execute(stmt)).scalar_one_or_none()
            assert task_rec is not None
            assert task_rec.user_request == user_request
            assert task_rec.status == "completed"
            assert task_rec.verification_passed is True

            act_stmt = select(AgentActivity).where(AgentActivity.task_id == task_id)
            activities = (await session.execute(act_stmt)).scalars().all()
            assert len(activities) >= 1
            agent_names = [a.agent_name for a in activities]
            assert "planner_agent" in agent_names or "research_agent" in agent_names
