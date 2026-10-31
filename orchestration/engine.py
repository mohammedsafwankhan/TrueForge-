"""
Multi-Agent Orchestration Engine.
Integrates LangGraph StateGraph with Fetch.ai Agent foundation.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agents.execution_agent import ExecutionAgent
from agents.planner_agent import PlannerAgent
from agents.research_agent import ResearchAgent
from agents.verification_agent import VerificationAgent
from core.config import Settings, get_settings
from core.logger import get_agent_logger
from db.connection import record_task_history, update_task_completion
from orchestration.asi_client import ASI1Client
from orchestration.state import WorkflowState
from orchestration.workflow import MultiAgentWorkflowBuilder
from tools.api_tools import register_api_tools
from tools.execution_tools import register_execution_tools
from tools.mcp_tools import register_mcp_tools
from tools.tool_registry import ToolRegistry, global_tool_registry

logger = get_agent_logger("orchestration.engine")


class MultiAgentEngine:
    """
    High-level facade orchestrating specialized agents through the LangGraph StateGraph.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.tool_registry = tool_registry or global_tool_registry

        # Register tools
        register_api_tools(self.tool_registry)
        register_execution_tools(self.tool_registry)
        self.mcp_client = register_mcp_tools(self.tool_registry)

        # Initialize ASI-1 client
        self.asi_client = ASI1Client(settings=self.settings)

        # Initialize Specialized Agents
        self.planner_agent = PlannerAgent(asi_client=self.asi_client, tool_registry=self.tool_registry)
        self.research_agent = ResearchAgent(tool_registry=self.tool_registry)
        self.execution_agent = ExecutionAgent(tool_registry=self.tool_registry)
        self.verification_agent = VerificationAgent(asi_client=self.asi_client)

        # Build Workflow Graph
        builder = MultiAgentWorkflowBuilder(
            planner_agent=self.planner_agent,
            research_agent=self.research_agent,
            execution_agent=self.execution_agent,
            verification_agent=self.verification_agent,
            asi_client=self.asi_client,
            tool_registry=self.tool_registry,
        )
        self.compiled_graph = builder.build_graph()

    async def execute_task(
        self,
        user_request: str,
        session_id: str,
        sender: str,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute an autonomous multi-agent task through the LangGraph pipeline.
        """
        t_id = task_id or str(uuid4())
        logger.info(f"Initiating autonomous task [{t_id}] for sender [{sender}]: '{user_request}'")

        # Initial database audit record
        await record_task_history(
            task_id=t_id,
            session_id=session_id,
            sender=sender,
            user_request=user_request,
            status="in_progress",
        )

        initial_state: WorkflowState = {
            "task_id": t_id,
            "session_id": session_id,
            "sender": sender,
            "user_request": user_request,
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

        # Execute compiled LangGraph StateGraph
        config = {"configurable": {"thread_id": t_id}}
        final_state = await self.compiled_graph.ainvoke(initial_state, config=config)

        final_response = final_state.get("final_response") or "Autonomous execution completed."
        is_valid = final_state.get("verification", {}).get("is_valid", True)

        # Update database completion record
        await update_task_completion(
            task_id=t_id,
            final_response=final_response,
            verification_passed=is_valid,
            status="completed" if is_valid else "completed_with_warnings",
        )

        logger.info(f"Task [{t_id}] completed with status: {final_state.get('status')}")
        return final_state


# Global default engine instance
_default_engine = None


def get_orchestration_engine() -> MultiAgentEngine:
    """Retrieve or lazily instantiate the global multi-agent engine."""
    global _default_engine
    if _default_engine is None:
        _default_engine = MultiAgentEngine()
    return _default_engine
