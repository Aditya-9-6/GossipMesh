import time
import logging
import asyncio
from functools import wraps
from typing import Type, Tuple, Optional, Callable, Any, AsyncGenerator
import inspect

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open."""

    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures.")

    def record_success(self):
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            logger.info("Circuit breaker closed after successful half-open request.")
        elif self.state == "CLOSED":
            self.failure_count = 0

    def check_state(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering half-open state.")
                return True
            return False
        return True


def with_retry_and_circuit_breaker(
    exceptions: Tuple[Type[Exception], ...],
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.isasyncgenfunction(func):

            @wraps(func)
            async def async_gen_wrapper(*args: Any, **kwargs: Any) -> AsyncGenerator[Any, None]:
                if circuit_breaker and not circuit_breaker.check_state():
                    raise CircuitBreakerOpenError(f"Circuit breaker is open for {func.__name__}")

                current_delay = delay
                for attempt in range(retries):
                    try:
                        async for item in func(*args, **kwargs):
                            yield item
                        if circuit_breaker:
                            circuit_breaker.record_success()
                        return
                    except exceptions as e:
                        if attempt == retries - 1:
                            if circuit_breaker:
                                circuit_breaker.record_failure()
                            raise e

                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed for {func.__name__}: {str(e)}. Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                raise Exception("Unexpected error in retry logic")

            return async_gen_wrapper
        else:

            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                if circuit_breaker and not circuit_breaker.check_state():
                    raise CircuitBreakerOpenError(f"Circuit breaker is open for {func.__name__}")

                current_delay = delay
                for attempt in range(retries):
                    try:
                        result = await func(*args, **kwargs)
                        if circuit_breaker:
                            circuit_breaker.record_success()
                        return result
                    except exceptions as e:
                        if attempt == retries - 1:
                            if circuit_breaker:
                                circuit_breaker.record_failure()
                            raise e

                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed for {func.__name__}: {str(e)}. Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

                raise Exception("Unexpected error in retry logic")

            return wrapper

    return decorator
