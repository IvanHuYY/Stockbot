"""Utility decorators for retry, rate limiting, and timing."""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any

import structlog

logger = structlog.get_logger()


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry a function on exception with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(
                            "Max retries exceeded",
                            func=func.__name__,
                            attempts=max_attempts,
                            error=str(e),
                        )
                        raise
                    logger.warning(
                        "Retrying",
                        func=func.__name__,
                        attempt=attempt,
                        delay=current_delay,
                        error=str(e),
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None  # unreachable

        return wrapper

    return decorator


def timed(func: Callable) -> Callable:
    """Log the execution time of a function."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug("Function timed", func=func.__name__, elapsed_seconds=round(elapsed, 3))
        return result

    return wrapper
