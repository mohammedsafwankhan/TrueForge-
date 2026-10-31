"""
Research Agent Implementation.
Retrieves real-time external information, interfaces with data feeds, and parses responses.
"""

from datetime import datetime, timezone
from typing import Any

from core.logger import get_agent_logger
from db.connection import log_agent_activity, log_tool_execution
from tools.tool_registry import ToolRegistry, ToolResult

logger = get_agent_logger("agents.research")


class ResearchAgent:
    """
    Specialized agent responsible for retrieving real-time data and parsing external API responses.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    async def execute_research(
        self,
        task_id: str,
        tool_name: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute an external data retrieval operation.
        """
        start = datetime.now(timezone.utc)
        logger.info(f"[ResearchAgent] Querying tool '{tool_name}' for task {task_id}")

        result: ToolResult = await self.tool_registry.execute(
            name=tool_name,
            params=params or {},
        )

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000.0

        # Audit log in database
        await log_agent_activity(
            task_id=task_id,
            agent_name="research_agent",
            action=f"query_{tool_name}",
            status="success" if result.success else "failure",
            details={"tool": tool_name, "success": result.success, "error": result.error},
            duration_ms=duration,
        )

        await log_tool_execution(
            task_id=task_id,
            tool_name=tool_name,
            parameters=params,
            result_data=result.data if isinstance(result.data, dict) else {"raw": str(result.data)},
            error_message=result.error,
            success=result.success,
            duration_ms=duration,
        )

        return {
            "tool": tool_name,
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "timestamp": result.timestamp.isoformat(),
        }
