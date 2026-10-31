"""
Unit Tests for Tool Registry, Real External APIs, and Execution Tools.
"""

import pytest

from tools.api_tools import fetch_token_price, fetch_weather_forecast, http_get_resource, register_api_tools
from tools.execution_tools import calculate_expression, format_data_table, register_execution_tools
from tools.mcp_tools import MCPToolClient, register_mcp_tools
from tools.tool_registry import ToolPermissionLevel, ToolRegistry


class TestToolRegistry:
    """Tests covering tool registration, permission levels, and timeout protection."""

    def test_tool_registration_and_listing(self) -> None:
        registry = ToolRegistry()

        def dummy_action(x: int) -> int:
            return x * 2

        registry.register(
            name="dummy_action",
            description="Doubles an integer",
            handler=dummy_action,
            permission_level=ToolPermissionLevel.SAFE_EXECUTION,
        )

        assert "dummy_action" in [t["name"] for t in registry.list_tools()]
        tool = registry.get_tool("dummy_action")
        assert tool.name == "dummy_action"
        assert tool.permission_level == ToolPermissionLevel.SAFE_EXECUTION

    @pytest.mark.asyncio
    async def test_tool_execution_success(self) -> None:
        registry = ToolRegistry()
        registry.register(
            name="multiply",
            description="Multiplies numbers",
            handler=lambda a, b: a * b,
        )
        res = await registry.execute("multiply", {"a": 6, "b": 7})
        assert res.success is True
        assert res.data == 42
        assert res.duration_ms > 0

    @pytest.mark.asyncio
    async def test_tool_permission_denied_without_approval(self) -> None:
        registry = ToolRegistry()
        registry.register(
            name="sensitive_action",
            description="Mutating action requiring approval",
            handler=lambda: "done",
            permission_level=ToolPermissionLevel.REQUIRES_APPROVAL,
        )
        res = await registry.execute("sensitive_action", user_approved=False)
        assert res.success is False
        assert "requires explicit user approval" in res.error

        # With approval
        approved_res = await registry.execute("sensitive_action", user_approved=True)
        assert approved_res.success is True


class TestRealExternalAPITools:
    """Tests covering real live external API integrations."""

    @pytest.mark.asyncio
    async def test_real_coingecko_fetch_token_price(self) -> None:
        """Verify real live CoinGecko pricing oracle for Fetch.ai ($FET)."""
        data = await fetch_token_price(token_id="fetch-ai", vs_currency="usd")
        assert data.get("asset") == "fetch-ai"
        assert "price" in data
        assert isinstance(data["price"], (int, float))
        assert data["price"] > 0
        assert data.get("oracle") == "CoinGecko REST API"

    @pytest.mark.asyncio
    async def test_real_open_meteo_weather(self) -> None:
        """Verify real live Open-Meteo REST API for weather telemetry."""
        data = await fetch_weather_forecast(latitude=51.5074, longitude=-0.1278)
        assert data.get("source") == "Open-Meteo REST API"
        assert "temperature_celsius" in data
        assert isinstance(data["temperature_celsius"], (int, float))


class TestExecutionTools:
    """Tests covering mathematical calculation and data formatting."""

    def test_calculate_expression_arithmetic(self) -> None:
        res = calculate_expression("100 * (1 - 0.05) + 12.5")
        assert res.get("status") == "computed"
        assert res.get("result") == 107.5

    def test_calculate_expression_disallowed_syntax(self) -> None:
        res = calculate_expression("__import__('os').system('ls')")
        assert res.get("status") == "failed"
        assert "Evaluation error" in res.get("error", "")

    def test_format_data_table(self) -> None:
        headers = ["Asset", "Price USD"]
        rows = [["FET", "1.25"], ["ETH", "3200.00"]]
        res = format_data_table(headers=headers, rows=rows)
        assert res["row_count"] == 2
        assert "| Asset | Price USD |" in res["markdown_table"]
        assert "| FET | 1.25 |" in res["markdown_table"]


class TestMCPTools:
    """Tests covering Model Context Protocol integration."""

    @pytest.mark.asyncio
    async def test_mcp_tool_registration_and_execution(self) -> None:
        registry = ToolRegistry()
        mcp_client = register_mcp_tools(registry)

        tool = registry.get_tool("mcp_fetchai_network_info")
        assert tool.is_mcp is True

        res = await registry.execute("mcp_fetchai_network_info")
        assert res.success is True
        assert res.data["native_token"] == "FET"
        assert "Tendermint" in res.data["consensus"]
