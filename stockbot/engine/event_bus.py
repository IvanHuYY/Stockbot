"""Simple publish/subscribe event bus for internal communication."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

import structlog

logger = structlog.get_logger()


class EventBus:
    """Simple synchronous event bus for internal component communication."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe a handler from an event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event to all subscribed handlers."""
        for handler in self._handlers.get(event_type, []):
            try:
                handler(data)
            except Exception:
                logger.exception("Event handler error", event_type=event_type)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._handlers.clear()
