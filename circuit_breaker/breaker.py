"""
Circuit Breaker implementation.

States: CLOSED → OPEN → HALF_OPEN → CLOSED
Re-uses the classic pattern (familiar from DRL fault-tolerance work).
"""
from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F")


class CBState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreakerError(Exception):
    """Raised when the circuit is OPEN and a call is rejected."""


class CircuitBreaker:
    """
    Parameters
    ----------
    failure_threshold  – consecutive failures before tripping OPEN
    recovery_timeout   – seconds to wait before attempting HALF_OPEN probe
    success_threshold  – successful probes needed to close from HALF_OPEN
    name               – identifier used in logs / metrics
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CBState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CBState:
        return self._state

    async def _trip_open(self) -> None:
        self._state = CBState.OPEN
        self._opened_at = time.monotonic()
        self._failure_count = 0
        logger.warning("CircuitBreaker[%s] → OPEN", self.name)

    async def _try_reset(self) -> None:
        if self._state == CBState.OPEN:
            elapsed = time.monotonic() - (self._opened_at or 0)
            if elapsed >= self.recovery_timeout:
                self._state = CBState.HALF_OPEN
                self._success_count = 0
                logger.info("CircuitBreaker[%s] → HALF_OPEN (probe)", self.name)

    async def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            await self._try_reset()

            if self._state == CBState.OPEN:
                raise CircuitBreakerError(
                    f"CircuitBreaker[{self.name}] is OPEN — rejecting call"
                )

        try:
            result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
        except Exception as exc:
            async with self._lock:
                self._failure_count += 1
                self._success_count = 0
                logger.error(
                    "CircuitBreaker[%s] failure %d/%d: %s",
                    self.name,
                    self._failure_count,
                    self.failure_threshold,
                    exc,
                )
                if self._failure_count >= self.failure_threshold:
                    await self._trip_open()
            raise

        async with self._lock:
            self._failure_count = 0
            if self._state == CBState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CBState.CLOSED
                    logger.info("CircuitBreaker[%s] → CLOSED", self.name)

        return result


def circuit_breaker(
    name: str,
    failure_threshold: int = 3,
    recovery_timeout: float = 30.0,
    fallback: Callable[..., Any] | None = None,
) -> Callable[[F], F]:
    """Decorator that wraps an async function with a circuit breaker.

    If ``fallback`` is provided it is called (with the same args) when the
    circuit is OPEN instead of raising.
    """
    cb = CircuitBreaker(name=name, failure_threshold=failure_threshold, recovery_timeout=recovery_timeout)

    def decorator(fn: F) -> F:
        @wraps(fn)  # type: ignore[arg-type]
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await cb.call(fn, *args, **kwargs)
            except CircuitBreakerError:
                if fallback is not None:
                    return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
