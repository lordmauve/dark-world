"""Utilities for working with asyncio."""

import asyncio
from functools import wraps


def start_coroutine(func):
    """Decorator to make a handler into a coroutine.

    The coroutine will run on the event loop, can sleep,
    and so on.

    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        asyncio.ensure_future(func(*args, **kwargs))
    return wrapper
