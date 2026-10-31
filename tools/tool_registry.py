"""
Tool Registry and Execution Manager for Autonomous Multi-Agent Operations.
Provides strict validation, timeout management, permission checks, and structured results.
"""

import asyncio
import inspect
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from core.exceptions import ToolNotFoundError, ToolPermissionDeniedError
from core.logger import get_agent_logger

logger = get_agent_logger("tools.tool_registry")


class ToolPermissionLevel(str, Enum):
    """Access control permission level required for a tool."""

    READ_ONLY = "read_only"
    SAFE_EXECUTION = "safe_execution"
    MUTATING = "mutating"
    REQUIRES_APPROVAL = "requires_approval"


class ToolResult(BaseModel):
    """
    Standardized result structure returned by all tools.
    """

    tool_name: str
    execution_id: UUID = Field(default_factory=uuid4)
    success: bool
    data: Any | None = None
    error: str | None = None
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_error(self) -> bool:
        return not self.success


class ToolDefinition(BaseModel):
    """
    Metadata specification for a registered agent tool.
    """

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    permission_level: ToolPermissionLevel = ToolPermissionLevel.READ_ONLY
    timeout_seconds: float = 15.0
    is_mcp: bool = False

    def to_descriptor(self) -> dict[str, Any]:
        """Convert to descriptor format consumable by ASI-1 and planners."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "permission_level": self.permission_level.value,
            "is_mcp": self.is_mcp,
        }


class ToolRegistry:
    """
    Central registry and execution harness for real external APIs, MCP tools, and operations.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        parameters: dict[str, Any] | None = None,
        permission_level: ToolPermissionLevel = ToolPermissionLevel.READ_ONLY,
        timeout_seconds: float = 15.0,
        is_mcp: bool = False,
    ) -> None:
        """Register a new callable tool."""
        defn = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters or {},
            permission_level=permission_level,
            timeout_seconds=timeout_seconds,
            is_mcp=is_mcp,
        )
        self._tools[name] = defn
        self._handlers[name] = handler
        logger.info(f"Registered tool: '{name}' [{permission_level.value}]")

    def get_tool(self, name: str) -> ToolDefinition:
        """Retrieve tool definition by name."""
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools as serializable descriptors."""
        return [tool.to_descriptor() for tool in self._tools.values()]

    async def execute(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        user_approved: bool = False,
    ) -> ToolResult:
        """
        Execute tool with parameter enforcement, permissions checking, and timeout guards.
        """
        if name not in self._tools or name not in self._handlers:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Tool '{name}' not found in registry.",
            )

        tool = self._tools[name]
        handler = self._handlers[name]
        kwargs = params or {}

        # Permission verification
        if tool.permission_level == ToolPermissionLevel.REQUIRES_APPROVAL and not user_approved:
            err_msg = f"Tool '{name}' requires explicit user approval before execution."
            logger.warning(err_msg)
            return ToolResult(tool_name=name, success=False, error=err_msg)

        start_time = datetime.now(timezone.utc)
        logger.info(f"Executing tool '{name}' with params: {kwargs}")

        try:
            # Execute with timeout guard
            if inspect.iscoroutinefunction(handler):
                result_data = await asyncio.wait_for(handler(**kwargs), timeout=tool.timeout_seconds)
            else:
                loop = asyncio.get_running_loop()
                result_data = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: handler(**kwargs)),
                    timeout=tool.timeout_seconds,
                )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            logger.info(f"Tool '{name}' completed successfully in {duration:.1f}ms")
            return ToolResult(
                tool_name=name,
                success=True,
                data=result_data,
                duration_ms=duration,
            )

        except asyncio.TimeoutError:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            err = f"Tool '{name}' timed out after {tool.timeout_seconds} seconds."
            logger.error(err)
            return ToolResult(tool_name=name, success=False, error=err, duration_ms=duration)

        except Exception as exc:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            err = f"Tool '{name}' execution error: {exc}"
            logger.exception(err)
            return ToolResult(tool_name=name, success=False, error=err, duration_ms=duration)


# Global default registry instance
global_tool_registry = ToolRegistry()
