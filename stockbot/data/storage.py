"""DuckDB-based persistent storage for market data."""

from __future__ import annotations

import os
from datetime import datetime

import duckdb
import pandas as pd
import structlog

logger = structlog.get_logger()


class MarketDataStore:
    """Persist and retrieve historical bars using DuckDB."""

    def __init__(self, db_path: str = "data/stockbot.duckdb") -> None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = duckdb.connect(db_path)
        self._init_tables()

    def _init_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS bars (
                symbol VARCHAR,
                timeframe VARCHAR,
                timestamp TIMESTAMP WITH TIME ZONE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                vwap DOUBLE,
                trade_count BIGINT,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)

    def save_bars(self, symbol: str, timeframe: str, df: pd.DataFrame) -> int:
        """Save bars to storage. Returns number of rows inserted."""
        if df.empty:
            return 0

        records = df.reset_index()
        records["symbol"] = symbol
        records["timeframe"] = timeframe

        # Rename columns to match schema
        col_map = {"timestamp": "timestamp"}
        records = records.rename(columns=col_map)

        # Upsert using INSERT OR REPLACE
        self._conn.execute("""
            INSERT OR REPLACE INTO bars
            SELECT symbol, timeframe, timestamp, open, high, low, close,
                   volume, vwap, trade_count
            FROM records
        """)

        logger.debug("Saved bars", symbol=symbol, timeframe=timeframe, rows=len(records))
        return len(records)

    def load_bars(
        self,
        symbol: str,
        timeframe: str = "1day",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        """Load bars from storage."""
        query = "SELECT * FROM bars WHERE symbol = ? AND timeframe = ?"
        params: list = [symbol, timeframe]

        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)

        query += " ORDER BY timestamp"
        df = self._conn.execute(query, params).fetchdf()

        if not df.empty:
            df = df.set_index("timestamp")
            df = df.drop(columns=["symbol", "timeframe"], errors="ignore")

        return df

    def get_available_range(self, symbol: str, timeframe: str = "1day") -> tuple | None:
        """Get the earliest and latest timestamp available for a symbol."""
        result = self._conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM bars WHERE symbol = ? AND timeframe = ?",
            [symbol, timeframe],
        ).fetchone()

        if result and result[0] is not None:
            return (result[0], result[1])
        return None

    def get_stored_symbols(self) -> list[str]:
        """List all symbols in storage."""
        result = self._conn.execute("SELECT DISTINCT symbol FROM bars").fetchall()
        return [r[0] for r in result]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
