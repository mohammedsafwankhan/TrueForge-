"""
Reliability and Resiliency Infrastructure.
Implements:
- Circuit Breaker pattern with failure thresholds and recovery timeouts.
- Exponential backoff retry policies.
- Centralized Agent Health Monitoring.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
import math
import random
import time
from typing import Any, Callable, Coroutine, TypeVar

from core.logger import get_agent_logger

logger = get_agent_logger("core.reliability")

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # Normal operation: requests pass through
    OPEN = "OPEN"            # Tripped: requests fail fast
    HALF_OPEN = "HALF_OPEN"  # Probing: test if downstream service has recovered


class CircuitBreakerOpenError(Exception):
    """Raised when an operation is attempted while circuit breaker is open."""


class CircuitBreaker:
    """
    Production-grade Circuit Breaker protecting external dependencies
    (such as ASI-1 API, CoinGecko, Open-Meteo, and Fetch.ai Ledger).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 4,
        recovery_timeout_sec: float = 30.0,
        expected_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.expected_exceptions = expected_exceptions

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = time.time()
        self.last_failure_time: float | None = None
        self.last_error_message: str | None = None

    def _update_state(self, new_state: CircuitState) -> None:
        if self.state != new_state:
            logger.warning(
                f"[CircuitBreaker:{self.name}] Transitioned: {self.state.value} -> {new_state.value}"
            )
            self.state = new_state
            self.last_state_change = time.time()

    def allow_request(self) -> bool:
        """Determine whether an incoming request is allowed to proceed."""
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if now - (self.last_failure_time or 0) >= self.recovery_timeout_sec:
                self._update_state(CircuitState.HALF_OPEN)
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        """Record successful invocation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:
                # Successfully recovered
                self.failure_count = 0
                self.success_count = 0
                self.last_error_message = None
                self._update_state(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self, exc: Exception) -> None:
        """Record failed invocation and trip circuit if threshold exceeded."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.last_error_message = str(exc)

        if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
            if self.failure_count >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
                self._update_state(CircuitState.OPEN)

    async def call(self, func: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any) -> T:
        """Execute an async function wrapped with circuit breaker protection."""
        if not self.allow_request():
            remaining = max(0.0, self.recovery_timeout_sec - (time.time() - (self.last_failure_time or 0)))
            err_msg = (
                f"Circuit breaker '{self.name}' is OPEN. Fast-failing request. "
                f"Downstream service degraded. Retry in {remaining:.1f}s."
            )
            logger.warning(err_msg)
            raise CircuitBreakerOpenError(err_msg)

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exceptions as exc:
            self.record_failure(exc)
            raise


async def retry_with_backoff(
    func: Callable[..., Coroutine[Any, Any, T]],
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute an async callable with exponential backoff and jitter.
    """
    delay = initial_delay
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retry_exceptions as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error(f"Retry limit ({max_retries}) reached. Failing operation: {exc}")
                raise

            sleep_time = delay * (1 + (random.random() * 0.1 if jitter else 0))
            logger.warning(
                f"Attempt {attempt}/{max_retries} failed ({exc}). Retrying in {sleep_time:.2f}s..."
            )
            await asyncio.sleep(sleep_time)
            delay *= backoff_factor

    if last_exc:
        raise last_exc
    raise RuntimeError("Unexpected end of retry loop")


class HealthTracker:
    """
    Centralized health monitor aggregating subsystem statuses.
    """

    def __init__(self) -> None:
        self.start_time = datetime.now(timezone.utc)
        self.subsystems: dict[str, dict[str, Any]] = {
            "agent_core": {"status": "healthy", "details": "Active uAgents 0.13.0 event loop"},
            "asi1_api": {"status": "healthy", "details": "Authenticated to api.asi1.ai"},
            "database": {"status": "healthy", "details": "SQLAlchemy operational"},
            "cache": {"status": "healthy", "details": "In-memory/Redis cache online"},
            "ledger": {"status": "healthy", "details": "CosmPy Dorado testnet client ready"},
        }
        self.circuit_breakers: dict[str, CircuitBreaker] = {}

    def register_circuit_breaker(self, breaker: CircuitBreaker) -> None:
        self.circuit_breakers[breaker.name] = breaker

    def update_subsystem(self, name: str, status: str, details: str | None = None) -> None:
        self.subsystems[name] = {
            "status": status,
            "details": details or "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_health_status(self) -> dict[str, Any]:
        """Return aggregated health status for /health endpoint and Agentverse monitoring."""
        now = datetime.now(timezone.utc)
        uptime_seconds = (now - self.start_time).total_seconds()

        overall_healthy = all(
            sub["status"] in ("healthy", "degraded")
            for sub in self.subsystems.values()
        )

        breakers_status = {
            name: {
                "state": b.state.value,
                "failure_count": b.failure_count,
                "last_error": b.last_error_message,
            }
            for name, b in self.circuit_breakers.items()
        }

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "uptime_seconds": round(uptime_seconds, 2),
            "timestamp": now.isoformat(),
            "subsystems": self.subsystems,
            "circuit_breakers": breakers_status,
        }


# Global health tracker instance
health_tracker = HealthTracker()
