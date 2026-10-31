"""
Tools Package for Stranger Builds 2026.
Contains tool registry, real external API tools, execution tools, and MCP adapters.
"""

from .api_tools import fetch_token_price, fetch_weather_forecast, http_get_resource, register_api_tools
from .execution_tools import calculate_expression, format_data_table, register_execution_tools
from .mcp_tools import MCPToolClient, register_mcp_tools
from .tool_registry import (
    ToolDefinition,
    ToolPermissionLevel,
    ToolRegistry,
    ToolResult,
    global_tool_registry,
)

__all__ = [
    "ToolRegistry",
    "ToolDefinition",
    "ToolResult",
    "ToolPermissionLevel",
    "global_tool_registry",
    "fetch_token_price",
    "fetch_weather_forecast",
    "http_get_resource",
    "calculate_expression",
    "format_data_table",
    "MCPToolClient",
    "register_api_tools",
    "register_execution_tools",
    "register_mcp_tools",
]
