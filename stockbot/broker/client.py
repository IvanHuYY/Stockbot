"""Unified Alpaca broker client."""

from __future__ import annotations

import structlog
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading import TradingClient

from config.settings import Settings
from stockbot.broker.account import AccountManager
from stockbot.broker.orders import OrderManager
from stockbot.broker.positions import PositionManager
from stockbot.broker.streams import StreamManager

logger = structlog.get_logger()


class AlpacaClient:
    """Unified broker client wrapping Alpaca's trading and data APIs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

        self.trading_client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=settings.paper_trading,
        )
        self.data_client = StockHistoricalDataClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
        )

        self._orders = OrderManager(self.trading_client)
        self._positions = PositionManager(self.trading_client)
        self._account = AccountManager(self.trading_client)
        self._streams: StreamManager | None = None

        mode = "paper" if settings.paper_trading else "LIVE"
        logger.info("Alpaca client initialized", mode=mode)

    @property
    def orders(self) -> OrderManager:
        return self._orders

    @property
    def positions(self) -> PositionManager:
        return self._positions

    @property
    def account(self) -> AccountManager:
        return self._account

    @property
    def streams(self) -> StreamManager:
        if self._streams is None:
            self._streams = StreamManager(
                api_key=self._settings.alpaca_api_key,
                secret_key=self._settings.alpaca_secret_key,
                paper=self._settings.paper_trading,
            )
        return self._streams
