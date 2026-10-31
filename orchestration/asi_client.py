"""
ASI-1 Primary Reasoning Engine Client.
Interfaces with the Artificial Superintelligence Alliance (ASI-1) model API.
"""

import json
import os
import re
from typing import Any

import httpx

from core.config import Settings, get_settings
from core.exceptions import ASI1AuthenticationError, ASI1ServiceError
from core.logger import get_agent_logger

logger = get_agent_logger("orchestration.asi_client")


class ASI1Client:
    """
    Production-grade HTTP client for ASI-1 runtime reasoning.
    Used for intent understanding, task planning, agent delegation, and result verification.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.api_key = self.settings.ASI1_API_KEY
        self.api_base = self.settings.ASI1_API_BASE.rstrip("/")
        self.model = self.settings.ASI1_MODEL or "asi1-mini"

        if not self.api_key:
            logger.warning("ASI1_API_KEY is not configured; ASI-1 client will raise when called.")

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ASI1AuthenticationError(
                "ASI-1 API key is not configured. Configure ASI1_API_KEY in .env."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def check_connectivity(self) -> dict[str, Any]:
        """
        Verify live authenticated connectivity with ASI-1 API.
        """
        headers = self._get_headers()
        url = f"{self.api_base}/models"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 401:
                    raise ASI1AuthenticationError("ASI-1 Authentication failed (HTTP 401 Unauthorized).")
                response.raise_for_status()
                data = response.json()
                logger.info(f"ASI-1 connectivity validated successfully: {len(data.get('data', []))} models available.")
                return data
            except httpx.HTTPStatusError as exc:
                raise ASI1ServiceError(f"ASI-1 API returned HTTP {exc.response.status_code}: {exc.response.text}") from exc
            except httpx.RequestError as exc:
                raise ASI1ServiceError(f"Network error connecting to ASI-1 at {url}: {exc}") from exc

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """
        Dispatch a chat completion request to ASI-1.
        """
        headers = self._get_headers()
        url = f"{self.api_base}/chat/completions"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 401:
                    raise ASI1AuthenticationError("ASI-1 API rejected authentication credentials.")
                response.raise_for_status()
                result = response.json()
                choices = result.get("choices", [])
                if not choices:
                    raise ASI1ServiceError("ASI-1 API returned empty choices list.")
                return choices[0]["message"]["content"] or ""
            except httpx.HTTPStatusError as exc:
                raise ASI1ServiceError(
                    f"ASI-1 chat completion failed ({exc.response.status_code}): {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise ASI1ServiceError(f"Connection failure to ASI-1 service: {exc}") from exc

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "You are a precise reasoning engine. Output valid JSON only.",
    ) -> dict[str, Any]:
        """
        Prompt ASI-1 and parse the output as valid JSON.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        raw_text = await self.complete(messages=messages, temperature=0.1)

        # Clean JSON markdown fences if present
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n?", "", clean_text)
            clean_text = re.sub(r"\n?```$", "", clean_text).strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to decode JSON from ASI-1 output: {raw_text}")
            raise ASI1ServiceError(f"ASI-1 produced invalid JSON output: {raw_text[:200]}") from exc

    async def plan_task(self, user_request: str, available_tools: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Decompose user request into structured subtasks with assigned specialized agents.
        """
        system_prompt = (
            "You are the Planner Agent powered by ASI-1 for Stranger Builds 2026.\n"
            "Analyze user requests and break them down into an ordered execution plan.\n"
            "Specialized agents:\n"
            "- 'planner': intent understanding and planning\n"
            "- 'research': external queries, web data retrieval, live crypto/metrics\n"
            "- 'execution': calling approved tools, executing calculations, storing data\n"
            "- 'verification': validating results and quality checks\n"
            "Output JSON with fields: 'intent' (str), 'subtasks' (list of objects with 'id', 'agent', 'action', 'tool', 'params', 'dependencies'), 'confidence' (float)."
        )
        prompt = (
            f"User Request: {user_request}\n"
            f"Available Registered Tools: {json.dumps(available_tools, indent=2)}\n\n"
            "Generate the optimal multi-agent execution plan in JSON."
        )
        return await self.generate_json(prompt=prompt, system_prompt=system_prompt)

    async def verify_outcome(
        self,
        goal: str,
        plan: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Verify execution results against the original user goal and detect failures.
        """
        system_prompt = (
            "You are the Verification Agent powered by ASI-1 for Stranger Builds 2026.\n"
            "Validate whether the execution results accurately and reliably fulfill the user goal.\n"
            "Detect failures, incomplete data, or hallucinations.\n"
            "Output JSON with: 'is_valid' (bool), 'quality_score' (0.0 to 1.0), 'reasoning' (str), 'needs_retry' (bool), 'failed_subtask_id' (optional int/str)."
        )
        prompt = (
            f"Original Goal: {goal}\n"
            f"Executed Plan: {json.dumps(plan, indent=2)}\n"
            f"Tool & Agent Results: {json.dumps(results, indent=2)}\n\n"
            "Perform rigorous validation and return verdict JSON."
        )
        return await self.generate_json(prompt=prompt, system_prompt=system_prompt)

    async def synthesize_final_response(
        self,
        user_request: str,
        results: list[dict[str, Any]],
        verification: dict[str, Any],
    ) -> str:
        """
        Synthesize the final human-readable response based on verified multi-agent execution.
        """
        system_prompt = (
            "You are the Primary Orchestrator Agent for Stranger Builds 2026.\n"
            "Synthesize a clear, authoritative, and structured final response for the user.\n"
            "Cite actual verified data retrieved by specialized agents. Be concise and professional."
        )
        prompt = (
            f"User Request: {user_request}\n"
            f"Verified Agent Results: {json.dumps(results, indent=2)}\n"
            f"Verification Verdict: {json.dumps(verification, indent=2)}\n\n"
            "Generate the final user response."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        return await self.complete(messages=messages, temperature=0.3)
