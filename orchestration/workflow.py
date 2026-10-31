"""
LangGraph Multi-Agent Autonomous Execution Workflow.
Coordinates Planner, Research, Execution, and Verification agents with conditional routing and checkpointing.
"""

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from core.logger import get_agent_logger
from orchestration.asi_client import ASI1Client
from orchestration.state import WorkflowState
from tools.tool_registry import ToolRegistry

if TYPE_CHECKING:
    from agents.execution_agent import ExecutionAgent
    from agents.planner_agent import PlannerAgent
    from agents.research_agent import ResearchAgent
    from agents.verification_agent import VerificationAgent

logger = get_agent_logger("orchestration.workflow")


class MultiAgentWorkflowBuilder:
    """
    Builder creating the compiled LangGraph execution graph connecting specialized agents.
    """

    def __init__(
        self,
        planner_agent: Any,
        research_agent: Any,
        execution_agent: Any,
        verification_agent: Any,
        asi_client: ASI1Client,
        tool_registry: ToolRegistry,
    ) -> None:
        self.planner_agent = planner_agent
        self.research_agent = research_agent
        self.execution_agent = execution_agent
        self.verification_agent = verification_agent
        self.asi_client = asi_client
        self.tool_registry = tool_registry

    def build_graph(self) -> Any:
        """
        Construct and compile the multi-agent state graph with conditional edges.
        """
        workflow = StateGraph(WorkflowState)

        # 1. Register Graph Nodes
        workflow.add_node("plan_node", self._plan_node)
        workflow.add_node("research_node", self._research_node)
        workflow.add_node("execution_node", self._execution_node)
        workflow.add_node("verification_node", self._verification_node)
        workflow.add_node("retry_node", self._retry_node)
        workflow.add_node("synthesize_node", self._synthesize_node)

        # 2. Edges
        # START -> plan_node
        workflow.add_edge(START, "plan_node")

        # plan_node -> conditional routing to first subtask or verification
        workflow.add_conditional_edges(
            "plan_node",
            self._route_next_subtask,
            {
                "research": "research_node",
                "execution": "execution_node",
                "verify": "verification_node",
                "synthesize": "synthesize_node",
            },
        )

        # research_node -> route to next subtask
        workflow.add_conditional_edges(
            "research_node",
            self._route_next_subtask,
            {
                "research": "research_node",
                "execution": "execution_node",
                "verify": "verification_node",
                "synthesize": "synthesize_node",
            },
        )

        # execution_node -> route to next subtask
        workflow.add_conditional_edges(
            "execution_node",
            self._route_next_subtask,
            {
                "research": "research_node",
                "execution": "execution_node",
                "verify": "verification_node",
                "synthesize": "synthesize_node",
            },
        )

        # verification_node -> conditionally route to synthesize or retry
        workflow.add_conditional_edges(
            "verification_node",
            self._route_verification_outcome,
            {
                "pass": "synthesize_node",
                "retry": "retry_node",
            },
        )

        # retry_node -> plan_node (re-attempt workflow with backoff)
        workflow.add_edge("retry_node", "plan_node")

        # synthesize_node -> END
        workflow.add_edge("synthesize_node", END)

        # Compile with in-memory checkpointer for state isolation and recovery
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    # -------------------------------------------------------------
    # Node Callbacks
    # -------------------------------------------------------------

    async def _plan_node(self, state: WorkflowState) -> dict[str, Any]:
        task_id = state.get("task_id", "unknown_task")
        user_request = state.get("user_request", "")
        logger.info(f"[Workflow:plan_node] Formulating execution plan for task: {task_id}")

        plan_data = await self.planner_agent.create_plan(
            task_id=task_id,
            user_request=user_request,
        )

        return {
            "intent": plan_data.get("intent"),
            "plan": plan_data.get("subtasks", []),
            "current_subtask_index": 0,
            "status": "planned",
        }

    async def _research_node(self, state: WorkflowState) -> dict[str, Any]:
        task_id = state.get("task_id", "")
        plan = state.get("plan", [])
        idx = state.get("current_subtask_index", 0)
        results = list(state.get("results", []))

        if idx < len(plan):
            subtask = plan[idx]
            tool_name = subtask.get("tool") or subtask.get("action", "")
            params = subtask.get("params", {})

            res = await self.research_agent.execute_research(
                task_id=task_id,
                tool_name=tool_name,
                params=params,
            )
            results.append({"subtask_id": subtask.get("id"), "agent": "research", "output": res})

        return {
            "results": results,
            "current_subtask_index": idx + 1,
            "status": "research_executed",
        }

    async def _execution_node(self, state: WorkflowState) -> dict[str, Any]:
        task_id = state.get("task_id", "")
        plan = state.get("plan", [])
        idx = state.get("current_subtask_index", 0)
        results = list(state.get("results", []))

        if idx < len(plan):
            subtask = plan[idx]
            tool_name = subtask.get("tool") or subtask.get("action", "")
            params = subtask.get("params", {})

            res = await self.execution_agent.execute_task(
                task_id=task_id,
                tool_name=tool_name,
                params=params,
                user_approved=True,  # In autonomous graph execution, approved for safe execution level
            )
            results.append({"subtask_id": subtask.get("id"), "agent": "execution", "output": res})

        return {
            "results": results,
            "current_subtask_index": idx + 1,
            "status": "action_executed",
        }

    async def _verification_node(self, state: WorkflowState) -> dict[str, Any]:
        task_id = state.get("task_id", "")
        goal = state.get("user_request", "")
        plan = state.get("plan", [])
        results = state.get("results", [])

        verdict = await self.verification_agent.verify_results(
            task_id=task_id,
            goal=goal,
            plan=plan,
            results=results,
        )

        return {
            "verification": verdict,
            "status": "verified" if verdict.get("is_valid") else "verification_failed",
        }

    async def _retry_node(self, state: WorkflowState) -> dict[str, Any]:
        retry_count = state.get("retry_count", 0) + 1
        # Exponential backoff
        backoff_seconds = min(2**retry_count, 8)
        logger.warning(
            f"[Workflow:retry_node] Verification failed. Initiating retry #{retry_count} "
            f"with {backoff_seconds}s backoff."
        )
        await asyncio.sleep(backoff_seconds)

        return {
            "retry_count": retry_count,
            "current_subtask_index": 0,
            "results": [],  # Clear flawed prior results
            "status": "retrying",
        }

    async def _synthesize_node(self, state: WorkflowState) -> dict[str, Any]:
        user_request = state.get("user_request", "")
        results = state.get("results", [])
        verification = state.get("verification", {"is_valid": True})

        try:
            final_text = await self.asi_client.synthesize_final_response(
                user_request=user_request,
                results=results,
                verification=verification,
            )
        except Exception as exc:
            logger.warning(f"[Workflow:synthesize_node] ASI-1 synthesis error ({exc}). Formatting results directly.")
            final_text = self._deterministic_synthesize(user_request, results, verification)

        return {
            "final_response": final_text,
            "status": "completed",
        }

    def _deterministic_synthesize(
        self,
        user_request: str,
        results: list[dict[str, Any]],
        verification: dict[str, Any],
    ) -> str:
        lines = [f"**Goal**: {user_request}\n"]
        for r in results:
            out = r.get("output", {})
            data = out.get("data")
            if isinstance(data, dict):
                for k, v in data.items():
                    lines.append(f"- **{k}**: {v}")
            elif data:
                lines.append(f"- {data}")

        if not verification.get("is_valid", True):
            lines.append(f"\n*(Verification Notice: {verification.get('reasoning')})*")

        return "\n".join(lines)

    # -------------------------------------------------------------
    # Conditional Routing Logic
    # -------------------------------------------------------------

    def _route_next_subtask(
        self,
        state: WorkflowState,
    ) -> Literal["research", "execution", "verify", "synthesize"]:
        plan = state.get("plan", [])
        idx = state.get("current_subtask_index", 0)

        # If all subtasks in plan are executed, route to verification
        if idx >= len(plan):
            return "verify"

        subtask = plan[idx]
        target_agent = str(subtask.get("agent", "")).lower()

        if target_agent == "research":
            return "research"
        elif target_agent == "execution":
            return "execution"
        elif target_agent == "verification":
            return "verify"
        else:
            # Fallback based on action/tool name
            action = str(subtask.get("action", "")).lower()
            if any(w in action for w in ["price", "weather", "fetch", "query", "mcp"]):
                return "research"
            elif any(w in action for w in ["calculate", "compute", "format", "store"]):
                return "execution"
            return "verify"

    def _route_verification_outcome(
        self,
        state: WorkflowState,
    ) -> Literal["pass", "retry"]:
        verification = state.get("verification", {})
        is_valid = verification.get("is_valid", False)
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)

        if is_valid or retry_count >= max_retries:
            return "pass"
        return "retry"
