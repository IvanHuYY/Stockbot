"""Market data fetching from Alpaca."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd
import structlog
from alpaca.data.requests import StockBarsRequest, StockLatestBarRequest, StockSnapshotRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

if TYPE_CHECKING:
    from alpaca.data.historical import StockHistoricalDataClient

logger = structlog.get_logger()

TIMEFRAME_MAP = {
    "1min": TimeFrame(1, TimeFrameUnit.Minute),
    "5min": TimeFrame(5, TimeFrameUnit.Minute),
    "15min": TimeFrame(15, TimeFrameUnit.Minute),
    "1hour": TimeFrame(1, TimeFrameUnit.Hour),
    "1day": TimeFrame(1, TimeFrameUnit.Day),
    "1week": TimeFrame(1, TimeFrameUnit.Week),
}


class MarketDataService:
    """Fetch historical and live market data from Alpaca."""

    def __init__(self, data_client: StockHistoricalDataClient) -> None:
        self._client = data_client

    def get_bars(
        self,
        symbol: str,
        timeframe: str = "1day",
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch historical bars for a symbol."""
        tf = TIMEFRAME_MAP.get(timeframe)
        if tf is None:
            raise ValueError(f"Unknown timeframe: {timeframe}. Use one of {list(TIMEFRAME_MAP)}")

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end,
            limit=limit,
        )
        bars = self._client.get_stock_bars(request)
        df = bars.df

        if isinstance(df.index, pd.MultiIndex):
            df = df.droplevel("symbol")

        logger.debug("Fetched bars", symbol=symbol, timeframe=timeframe, rows=len(df))
        return df

    def get_multi_bars(
        self,
        symbols: list[str],
        timeframe: str = "1day",
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Fetch historical bars for multiple symbols."""
        tf = TIMEFRAME_MAP.get(timeframe)
        if tf is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")

        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=tf,
            start=start,
            end=end,
            limit=limit,
        )
        bars = self._client.get_stock_bars(request)
        df = bars.df

        result = {}
        if isinstance(df.index, pd.MultiIndex) and "symbol" in df.index.names:
            for sym in symbols:
                try:
                    result[sym] = df.loc[sym]
                except KeyError:
                    logger.warning("No data for symbol", symbol=sym)
                    result[sym] = pd.DataFrame()
        else:
            # Single symbol case
            result[symbols[0]] = df

        logger.debug("Fetched multi bars", symbols=symbols, timeframe=timeframe)
        return result

    def get_latest_bars(self, symbols: list[str]) -> dict:
        """Get the latest bar for each symbol."""
        request = StockLatestBarRequest(symbol_or_symbols=symbols)
        return self._client.get_stock_latest_bar(request)

    def get_snapshot(self, symbol: str) -> dict:
        """Get latest snapshot (bar + quote + trade) for a symbol."""
        request = StockSnapshotRequest(symbol_or_symbols=symbol)
        snapshot = self._client.get_stock_snapshot(request)
        return snapshot
