"""Main trading runner - orchestrates the trading loop."""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog
import yaml

from config.logging_config import setup_logging
from config.settings import Settings
from stockbot.agents.graph import build_trading_graph
from stockbot.broker.client import AlpacaClient
from stockbot.db.session import init_db
from stockbot.engine.scheduler import TradingScheduler

logger = structlog.get_logger()


class TradingRunner:
    """Main trading loop that invokes the agent pipeline on schedule."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        setup_logging(self._settings.log_level)

        self._broker = AlpacaClient(self._settings)
        self._graph = build_trading_graph(self._broker, self._settings)
        self._scheduler = TradingScheduler(self._settings)
        self._running = False
        self._symbols = self._load_watchlist()

        # Initialize database
        init_db()

    def _load_watchlist(self) -> list[str]:
        """Load trading symbols from config."""
        config_path = Path("config/symbols.yaml")
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
                return data.get("watchlist", [])
        return ["AAPL", "MSFT", "GOOGL"]

    async def run(self) -> None:
        """Start the main trading loop."""
        self._running = True
        mode = "PAPER" if self._settings.paper_trading else "LIVE"
        logger.info(
            "Trading runner started",
            mode=mode,
            symbols=self._symbols,
            cycle_minutes=self._settings.trading_cycle_minutes,
        )

        while self._running:
            try:
                await self._scheduler.wait_for_next_cycle()

                if not self._running:
                    break

                await self._run_cycle()

            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                self._running = False
            except Exception:
                logger.exception("Cycle error, will retry next cycle")
                await asyncio.sleep(60)

        logger.info("Trading runner stopped")

    async def _run_cycle(self) -> None:
        """Run a single trading cycle through the agent pipeline."""
        logger.info("Starting trading cycle", symbols=len(self._symbols))

        initial_state = {
            "messages": [],
            "symbols_to_analyze": self._symbols,
            "market_data": {},
            "news_data": [],
            "account_info": {},
            "current_positions": [],
            "analyses": [],
            "risk_assessments": [],
            "trade_decisions": [],
            "execution_results": [],
            "cycle_id": "",
            "cycle_timestamp": "",
        }

        result = await asyncio.to_thread(self._graph.invoke, initial_state)

        # Log summary
        decisions = result.get("trade_decisions", [])
        executions = result.get("execution_results", [])
        trades = [d for d in decisions if d["action"] != "hold"]
        executed = [e for e in executions if e["status"] == "submitted"]

        logger.info(
            "Cycle complete",
            cycle_id=result.get("cycle_id", "?"),
            symbols_analyzed=len(result.get("analyses", [])),
            trades_decided=len(trades),
            orders_submitted=len(executed),
        )

    def stop(self) -> None:
        """Stop the trading loop."""
        self._running = False
        logger.info("Stop signal sent")

    async def run_single_cycle(self) -> dict:
        """Run a single cycle and return the result (useful for testing)."""
        initial_state = {
            "messages": [],
            "symbols_to_analyze": self._symbols,
            "market_data": {},
            "news_data": [],
            "account_info": {},
            "current_positions": [],
            "analyses": [],
            "risk_assessments": [],
            "trade_decisions": [],
            "execution_results": [],
            "cycle_id": "",
            "cycle_timestamp": "",
        }
        return await asyncio.to_thread(self._graph.invoke, initial_state)
