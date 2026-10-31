"""
Planner Agent Implementation.
Understands user intent, decomposes requests into subtasks, and assigns dependencies.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from core.logger import get_agent_logger
from db.connection import log_agent_activity
from orchestration.asi_client import ASI1Client
from tools.tool_registry import ToolRegistry

logger = get_agent_logger("agents.planner")


class PlannerAgent:
    """
    Specialized agent responsible for strategic task decomposition and delegation planning.
    """

    def __init__(self, asi_client: ASI1Client, tool_registry: ToolRegistry) -> None:
        self.asi_client = asi_client
        self.tool_registry = tool_registry

    async def create_plan(
        self,
        task_id: str,
        user_request: str,
        context_memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Decompose a user request into an ordered, dependency-aware multi-agent plan.
        """
        start = datetime.now(timezone.utc)
        logger.info(f"[PlannerAgent] Planning for task {task_id}: '{user_request}'")

        tools_list = self.tool_registry.list_tools()

        try:
            plan_data = await self.asi_client.plan_task(
                user_request=user_request,
                available_tools=tools_list,
            )
        except Exception as exc:
            logger.warning(f"[PlannerAgent] ASI-1 planning error ({exc}). Generating rule-based deterministic plan.")
            # Deterministic fallback plan if remote LLM throws transient error
            plan_data = self._generate_fallback_plan(user_request)

        # Enforce minimum plan schema
        if "subtasks" not in plan_data or not isinstance(plan_data["subtasks"], list):
            plan_data["subtasks"] = self._generate_fallback_plan(user_request)["subtasks"]

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000.0
        await log_agent_activity(
            task_id=task_id,
            agent_name="planner_agent",
            action="create_plan",
            status="success",
            details={"subtask_count": len(plan_data.get("subtasks", [])), "intent": plan_data.get("intent")},
            duration_ms=duration,
        )

        logger.info(f"[PlannerAgent] Plan created with {len(plan_data['subtasks'])} subtasks.")
        return plan_data

    def _generate_fallback_plan(self, user_request: str) -> dict[str, Any]:
        req_lower = user_request.lower()
        subtasks = []

        if any(w in req_lower for w in ["price", "fet", "fetch", "crypto", "market", "eth", "btc"]):
            token = "fetch-ai"
            if "eth" in req_lower:
                token = "ethereum"
            elif "btc" in req_lower:
                token = "bitcoin"
            subtasks.append({
                "id": 1,
                "agent": "research",
                "action": "fetch_token_price",
                "tool": "fetch_token_price",
                "params": {"token_id": token, "vs_currency": "usd"},
                "dependencies": [],
            })
        elif "weather" in req_lower:
            subtasks.append({
                "id": 1,
                "agent": "research",
                "action": "fetch_weather_forecast",
                "tool": "fetch_weather_forecast",
                "params": {"latitude": 51.5074, "longitude": -0.1278},
                "dependencies": [],
            })
        elif any(c in req_lower for c in ["+", "-", "*", "/", "calculate", "compute"]):
            subtasks.append({
                "id": 1,
                "agent": "execution",
                "action": "calculate_expression",
                "tool": "calculate_expression",
                "params": {"expression": user_request},
                "dependencies": [],
            })
        else:
            subtasks.append({
                "id": 1,
                "agent": "research",
                "action": "mcp_fetchai_network_info",
                "tool": "mcp_fetchai_network_info",
                "params": {},
                "dependencies": [],
            })

        # Final verification step
        subtasks.append({
            "id": len(subtasks) + 1,
            "agent": "verification",
            "action": "verify_results",
            "tool": None,
            "params": {},
            "dependencies": [s["id"] for s in subtasks],
        })

        return {
            "intent": "autonomous_multi_agent_query",
            "subtasks": subtasks,
            "confidence": 0.95,
        }
