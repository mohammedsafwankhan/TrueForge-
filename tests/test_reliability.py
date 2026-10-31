"""
Unit tests for Reliability, Circuit Breaker, Exponential Backoff, and Health Tracking.
"""

import asyncio
import pytest

from core.reliability import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    HealthTracker,
    retry_with_backoff,
)


@pytest.mark.asyncio
async def test_circuit_breaker_tripping_and_recovering():
    """Verify circuit breaker trips to OPEN after threshold failures and recovers."""
    breaker = CircuitBreaker("test_breaker", failure_threshold=2, recovery_timeout_sec=0.1)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True

    # Record first failure
    breaker.record_failure(ValueError("Downstream timeout 1"))
    assert breaker.state == CircuitState.CLOSED

    # Record second failure -> trips to OPEN
    breaker.record_failure(ValueError("Downstream timeout 2"))
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False

    # Calling via breaker should fail fast
    async def dummy_fn():
        return "ok"

    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(dummy_fn)

    # Wait for recovery timeout
    await asyncio.sleep(0.12)
    assert breaker.allow_request() is True
    assert breaker.state == CircuitState.HALF_OPEN

    # Two successful calls in HALF_OPEN reset to CLOSED
    breaker.record_success()
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_retry_with_backoff_success():
    """Verify retry recovers after transient failures."""
    attempts = 0

    async def flaky_task():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Transient network drop")
        return "success_result"

    result = await retry_with_backoff(flaky_task, max_retries=3, initial_delay=0.01)
    assert result == "success_result"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_exhaustion():
    """Verify exception is raised when retries are exhausted."""
    async def always_fails():
        raise RuntimeError("Permanent failure")

    with pytest.raises(RuntimeError):
        await retry_with_backoff(always_fails, max_retries=2, initial_delay=0.01)


def test_health_tracker():
    """Verify aggregated health monitoring."""
    tracker = HealthTracker()
    status = tracker.get_health_status()
    assert status["status"] == "healthy"
    assert "agent_core" in status["subsystems"]
    assert "asi1_api" in status["subsystems"]
    assert status["uptime_seconds"] >= 0.0
