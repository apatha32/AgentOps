"""Unit tests for CircuitBreaker."""
import asyncio
import pytest
from circuit_breaker.breaker import CircuitBreaker, CircuitBreakerError, CBState


@pytest.mark.asyncio
async def test_closed_on_success():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=1)
    result = await cb.call(asyncio.coroutine(lambda: "ok")())
    # Works via the fn interface
    async def fn():
        return "ok"
    result = await cb.call(fn)
    assert result == "ok"
    assert cb.state == CBState.CLOSED


@pytest.mark.asyncio
async def test_trips_open_after_threshold():
    cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=30)

    async def failing():
        raise ValueError("boom")

    for _ in range(2):
        with pytest.raises(ValueError):
            await cb.call(failing)

    assert cb.state == CBState.OPEN


@pytest.mark.asyncio
async def test_open_rejects_immediately():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=30)

    async def failing():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await cb.call(failing)

    with pytest.raises(CircuitBreakerError):
        await cb.call(failing)


@pytest.mark.asyncio
async def test_half_open_after_recovery_timeout():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.05)

    async def failing():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await cb.call(failing)

    assert cb.state == CBState.OPEN
    await asyncio.sleep(0.1)

    async def succeeding():
        return "ok"

    result = await cb.call(succeeding)
    assert result == "ok"
