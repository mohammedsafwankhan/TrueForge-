"""
Real External REST API Integrations for Stranger Builds 2026.
Provides live token pricing, weather telemetry, and HTTP resource retrieval.
"""

from typing import Any

import httpx

from core.logger import get_agent_logger
from tools.tool_registry import ToolPermissionLevel, ToolRegistry

logger = get_agent_logger("tools.api_tools")


async def fetch_token_price(token_id: str = "fetch-ai", vs_currency: str = "usd") -> dict[str, Any]:
    """
    Query real-time crypto asset metrics (price, 24h change, currency) from CoinGecko API.

    Args:
        token_id: Asset identifier (e.g., 'fetch-ai', 'ethereum', 'bitcoin').
        vs_currency: Quote currency (e.g., 'usd', 'eur', 'gbp').
    """
    clean_id = token_id.strip().lower()
    clean_curr = vs_currency.strip().lower()

    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={clean_id}&vs_currencies={clean_curr}&include_24hr_change=true"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        if clean_id not in data:
            return {
                "asset": clean_id,
                "error": f"Asset '{clean_id}' not found on public pricing oracle.",
            }

        asset_data = data[clean_id]
        return {
            "asset": clean_id,
            "currency": clean_curr,
            "price": asset_data.get(clean_curr),
            "change_24h_percent": asset_data.get(f"{clean_curr}_24h_change"),
            "oracle": "CoinGecko REST API",
        }


async def fetch_weather_forecast(latitude: float = 51.5074, longitude: float = -0.1278) -> dict[str, Any]:
    """
    Retrieve real-time meteorological metrics from Open-Meteo REST API.

    Args:
        latitude: Geographic latitude (-90.0 to 90.0).
        longitude: Geographic longitude (-180.0 to 180.0).
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}&current_weather=true"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        current = data.get("current_weather", {})
        return {
            "latitude": latitude,
            "longitude": longitude,
            "temperature_celsius": current.get("temperature"),
            "windspeed_kmh": current.get("windspeed"),
            "weather_code": current.get("weathercode"),
            "timestamp": current.get("time"),
            "source": "Open-Meteo REST API",
        }


async def http_get_resource(url: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
    """
    Perform an authenticated or public HTTP GET request to retrieve external data.

    Args:
        url: Target HTTP or HTTPS URL.
        timeout_seconds: Request timeout in seconds.
    """
    headers = {"User-Agent": "StrangerBuilds-Agent/0.2.0"}
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.get(url, headers=headers)
        return {
            "status_code": response.status_code,
            "url": str(response.url),
            "headers": dict(response.headers),
            "body": response.text[:2000],  # truncated preview
        }


def register_api_tools(registry: ToolRegistry) -> None:
    """Register all REST API tools into the specified registry."""
    registry.register(
        name="fetch_token_price",
        description="Fetch live market price and 24h change for crypto assets like fetch-ai ($FET), ethereum, and bitcoin.",
        handler=fetch_token_price,
        parameters={
            "token_id": {"type": "string", "default": "fetch-ai", "description": "Token slug"},
            "vs_currency": {"type": "string", "default": "usd", "description": "Quote currency"},
        },
        permission_level=ToolPermissionLevel.READ_ONLY,
    )
    registry.register(
        name="fetch_weather_forecast",
        description="Query live temperature, windspeed, and weather conditions for geographic coordinates.",
        handler=fetch_weather_forecast,
        parameters={
            "latitude": {"type": "number", "default": 51.5074},
            "longitude": {"type": "number", "default": -0.1278},
        },
        permission_level=ToolPermissionLevel.READ_ONLY,
    )
    registry.register(
        name="http_get_resource",
        description="Inspect an external HTTP/HTTPS URL and return status code and response payload preview.",
        handler=http_get_resource,
        parameters={"url": {"type": "string", "required": True}},
        permission_level=ToolPermissionLevel.READ_ONLY,
    )
