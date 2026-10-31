"""
Unit and Live Integration Tests for ASI-1 Primary Reasoning Engine Client.
"""

import pytest
from core.config import Settings
from core.exceptions import ASI1AuthenticationError
from orchestration.asi_client import ASI1Client


class TestASI1Client:
    """Tests covering ASI-1 API connectivity, planning, and verification."""

    def test_client_initialization_missing_key_raises_on_call(self) -> None:
        """Verify client raises ASI1AuthenticationError when API key is absent."""
        empty_settings = Settings(ASI1_API_KEY=None)
        client = ASI1Client(settings=empty_settings)
        with pytest.raises(ASI1AuthenticationError):
            client._get_headers()

    @pytest.mark.asyncio
    async def test_live_connectivity_check(self) -> None:
        """Verify live authenticated connectivity to ASI-1 API."""
        client = ASI1Client()
        models_data = await client.check_connectivity()
        assert "data" in models_data
        model_ids = [m.get("id") for m in models_data.get("data", [])]
        assert "asi1-mini" in model_ids or "asi1" in model_ids

    @pytest.mark.asyncio
    async def test_live_completion(self) -> None:
        """Verify live chat completion with ASI-1 primary model."""
        client = ASI1Client()
        messages = [
            {"role": "user", "content": "Respond with the single word: ACKNOWLEDGED"}
        ]
        response = await client.complete(messages=messages, max_tokens=15)
        assert len(response.strip()) > 0
        assert "ACKNOWLEDGED" in response.upper()

    @pytest.mark.asyncio
    async def test_live_generate_json(self) -> None:
        """Verify structured JSON generation with ASI-1."""
        client = ASI1Client()
        prompt = "Return a JSON object with keys 'status' ('ok') and 'agent' ('primary')."
        data = await client.generate_json(prompt=prompt)
        assert isinstance(data, dict)
        assert data.get("status") == "ok"
        assert data.get("agent") == "primary"

    @pytest.mark.asyncio
    async def test_live_task_planning(self) -> None:
        """Verify ASI-1 plan_task breaks request into subtasks."""
        client = ASI1Client()
        available_tools = [
            {"name": "fetch_token_price", "description": "Get crypto price"},
            {"name": "calculate_expression", "description": "Evaluate math"},
        ]
        plan = await client.plan_task(
            user_request="Find the price of fetch-ai and calculate 100 times that price.",
            available_tools=available_tools,
        )
        assert "subtasks" in plan
        assert len(plan["subtasks"]) >= 1

    @pytest.mark.asyncio
    async def test_live_verification_evaluation(self) -> None:
        """Verify ASI-1 verify_outcome validates execution results."""
        client = ASI1Client()
        goal = "Get fetch-ai price"
        plan = [{"id": 1, "action": "fetch_token_price"}]
        results = [{"subtask_id": 1, "success": True, "output": {"price": 1.25, "asset": "fetch-ai"}}]

        verdict = await client.verify_outcome(goal=goal, plan=plan, results=results)
        assert "is_valid" in verdict
        assert isinstance(verdict["is_valid"], bool)
