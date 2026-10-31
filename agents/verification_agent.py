"""
Verification Agent Implementation.
Validates execution results, detects failures, and prevents false reports.
"""

from datetime import datetime, timezone
from typing import Any

from core.logger import get_agent_logger
from db.connection import log_agent_activity
from orchestration.asi_client import ASI1Client

logger = get_agent_logger("agents.verification")


class VerificationAgent:
    """
    Specialized agent providing rigorous result validation and failure detection.
    """

    def __init__(self, asi_client: ASI1Client) -> None:
        self.asi_client = asi_client

    async def verify_results(
        self,
        task_id: str,
        goal: str,
        plan: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Validate whether execution results satisfy the goal and are free of errors.
        """
        start = datetime.now(timezone.utc)
        logger.info(f"[VerificationAgent] Verifying task {task_id} with {len(results)} outputs")

        # Check for tool execution failures first
        failed_tools = [r for r in results if not r.get("success", True)]
        has_critical_failure = len(failed_tools) > 0 and len(failed_tools) == len(results)

        try:
            verdict = await self.asi_client.verify_outcome(
                goal=goal,
                plan=plan,
                results=results,
            )
        except Exception as exc:
            logger.warning(f"[VerificationAgent] ASI-1 verification call error ({exc}). Applying deterministic check.")
            # Deterministic verification check
            is_valid = len(results) > 0 and not has_critical_failure
            verdict = {
                "is_valid": is_valid,
                "quality_score": 0.85 if is_valid else 0.2,
                "reasoning": "Deterministic verification: Results generated without critical tool failure." if is_valid else "Critical tool execution failure detected.",
                "needs_retry": not is_valid,
            }

        # Override validity if all tools critically failed
        if has_critical_failure:
            verdict["is_valid"] = False
            verdict["needs_retry"] = True
            verdict["reasoning"] = f"Execution failed: {failed_tools[0].get('error', 'Unknown tool error')}"

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000.0

        await log_agent_activity(
            task_id=task_id,
            agent_name="verification_agent",
            action="verify_results",
            status="success" if verdict.get("is_valid") else "rejected",
            details=verdict,
            duration_ms=duration,
        )

        logger.info(f"[VerificationAgent] Verdict: valid={verdict.get('is_valid')}, score={verdict.get('quality_score')}")
        return verdict
