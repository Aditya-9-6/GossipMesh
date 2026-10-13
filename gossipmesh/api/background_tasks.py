import functools
from fastapi import BackgroundTasks
from typing import Callable, Any
from gossipmesh.middleware.correlation import correlation_id, get_correlation_id

class CorrelationIdBackgroundTasks(BackgroundTasks):
    def add_task(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """
        Add a background task, preserving the current correlation ID.
        """
        try:
            current_id = get_correlation_id()
        except LookupError:
            current_id = ""

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            token = correlation_id.set(current_id)
            try:
                return await func(*args, **kwargs)
            finally:
                correlation_id.reset(token)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            token = correlation_id.set(current_id)
            try:
                return func(*args, **kwargs)
            finally:
                correlation_id.reset(token)

        import inspect
        if inspect.iscoroutinefunction(func):
            super().add_task(async_wrapper, *args, **kwargs)
        else:
            super().add_task(sync_wrapper, *args, **kwargs)
