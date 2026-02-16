"""WebSocket streaming for real-time market data and trade updates."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog
from alpaca.data.live import StockDataStream

logger = structlog.get_logger()


class StreamManager:
    def __init__(self, api_key: str, secret_key: str, paper: bool = True) -> None:
        feed = "iex" if paper else "sip"
        self._stream = StockDataStream(api_key=api_key, secret_key=secret_key, feed=feed)
        self._handlers: dict[str, list[Callable]] = {
            "bar": [],
            "quote": [],
            "trade_update": [],
        }

    def subscribe_bars(self, symbols: list[str], handler: Callable) -> None:
        """Subscribe to minute bar updates for symbols."""
        self._handlers["bar"].append(handler)
        self._stream.subscribe_bars(self._on_bar, *symbols)
        logger.info("Subscribed to bars", symbols=symbols)

    def subscribe_quotes(self, symbols: list[str], handler: Callable) -> None:
        """Subscribe to real-time quote updates."""
        self._handlers["quote"].append(handler)
        self._stream.subscribe_quotes(self._on_quote, *symbols)
        logger.info("Subscribed to quotes", symbols=symbols)

    def subscribe_trade_updates(self, handler: Callable) -> None:
        """Subscribe to order fill / trade update notifications."""
        self._handlers["trade_update"].append(handler)
        self._stream.subscribe_trade_updates(self._on_trade_update)
        logger.info("Subscribed to trade updates")

    async def _on_bar(self, bar: Any) -> None:
        for handler in self._handlers["bar"]:
            try:
                await handler(bar) if asyncio_iscoroutinefunction(handler) else handler(bar)
            except Exception:
                logger.exception("Error in bar handler", symbol=bar.symbol)

    async def _on_quote(self, quote: Any) -> None:
        for handler in self._handlers["quote"]:
            try:
                await handler(quote) if asyncio_iscoroutinefunction(handler) else handler(quote)
            except Exception:
                logger.exception("Error in quote handler", symbol=quote.symbol)

    async def _on_trade_update(self, update: Any) -> None:
        for handler in self._handlers["trade_update"]:
            try:
                await handler(update) if asyncio_iscoroutinefunction(handler) else handler(update)
            except Exception:
                logger.exception("Error in trade update handler")

    def run(self) -> None:
        """Start the WebSocket stream (blocking)."""
        logger.info("Starting WebSocket stream")
        self._stream.run()

    async def stop(self) -> None:
        """Stop the WebSocket stream."""
        await self._stream.stop()
        logger.info("WebSocket stream stopped")


def asyncio_iscoroutinefunction(func: Callable) -> bool:
    """Check if a function is an async coroutine."""
    import asyncio

    return asyncio.iscoroutinefunction(func)
