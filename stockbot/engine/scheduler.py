"""Market-hours-aware trading scheduler."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import structlog

from config.settings import Settings
from stockbot.utils.market_hours import is_market_open, next_market_open

logger = structlog.get_logger()


class TradingScheduler:
    """Schedule trading cycles during market hours."""

    def __init__(self, settings: Settings) -> None:
        self._cycle_minutes = settings.trading_cycle_minutes
        self._last_cycle: datetime | None = None

    async def wait_for_next_cycle(self) -> None:
        """Wait until the next scheduled trading cycle.

        If market is closed, sleep until market opens.
        If market is open, wait for the next cycle interval.
        """
        while True:
            now = datetime.now()

            if not is_market_open(now):
                next_open = next_market_open(now)
                wait_seconds = max(0, (next_open - now).total_seconds())
                if wait_seconds > 60:
                    logger.info(
                        "Market closed, waiting for open",
                        next_open=next_open.isoformat(),
                        wait_minutes=round(wait_seconds / 60, 1),
                    )
                await asyncio.sleep(min(wait_seconds, 300))  # Check every 5 min max
                continue

            # Market is open - check if we should run a cycle
            if self._last_cycle is None:
                self._last_cycle = now
                logger.info("First cycle of the session")
                return

            elapsed = (now - self._last_cycle).total_seconds()
            cycle_seconds = self._cycle_minutes * 60

            if elapsed >= cycle_seconds:
                self._last_cycle = now
                logger.info(
                    "Starting new cycle",
                    interval_minutes=self._cycle_minutes,
                    elapsed_seconds=round(elapsed, 0),
                )
                return

            # Wait for remaining time
            remaining = cycle_seconds - elapsed
            logger.debug("Waiting for next cycle", remaining_seconds=round(remaining, 0))
            await asyncio.sleep(min(remaining, 30))  # Check every 30s

    def force_cycle(self) -> None:
        """Force the next cycle to run immediately."""
        self._last_cycle = None
        logger.info("Forced cycle triggered")
