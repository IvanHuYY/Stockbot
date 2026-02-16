"""Feature engineering - compute technical indicators from OHLCV data."""

from __future__ import annotations

import pandas as pd
import pandas_ta as ta
import structlog

logger = structlog.get_logger()


class FeatureEngineer:
    """Compute technical indicators and derived features from OHLCV data."""

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all standard technical indicators. Returns df with new columns."""
        if df.empty or len(df) < 2:
            return df

        result = df.copy()

        # Trend indicators
        result["sma_20"] = ta.sma(result["close"], length=20)
        result["sma_50"] = ta.sma(result["close"], length=50)
        result["sma_200"] = ta.sma(result["close"], length=200)
        result["ema_9"] = ta.ema(result["close"], length=9)
        result["ema_21"] = ta.ema(result["close"], length=21)

        # Momentum indicators
        result["rsi_14"] = ta.rsi(result["close"], length=14)
        result["rsi_7"] = ta.rsi(result["close"], length=7)

        macd = ta.macd(result["close"], fast=12, slow=26, signal=9)
        if macd is not None:
            result = pd.concat([result, macd], axis=1)

        stoch = ta.stoch(result["high"], result["low"], result["close"])
        if stoch is not None:
            result = pd.concat([result, stoch], axis=1)

        result["adx"] = ta.adx(result["high"], result["low"], result["close"])
        if isinstance(result["adx"], pd.DataFrame):
            adx_df = ta.adx(result["high"], result["low"], result["close"])
            result = result.drop(columns=["adx"])
            result = pd.concat([result, adx_df], axis=1)

        # Volatility indicators
        bbands = ta.bbands(result["close"], length=20, std=2.0)
        if bbands is not None:
            result = pd.concat([result, bbands], axis=1)

        result["atr_14"] = ta.atr(result["high"], result["low"], result["close"], length=14)

        # Volume indicators
        result["obv"] = ta.obv(result["close"], result["volume"])

        if "vwap" not in result.columns:
            result["vwap"] = ta.vwap(
                result["high"], result["low"], result["close"], result["volume"]
            )

        # Derived features
        result["price_change_1d"] = result["close"].pct_change(1)
        result["price_change_5d"] = result["close"].pct_change(5)
        result["price_change_20d"] = result["close"].pct_change(20)

        vol_sma = ta.sma(result["volume"].astype(float), length=20)
        result["volume_sma_ratio"] = result["volume"] / vol_sma

        # Distance from 52-week high/low (using rolling 252 trading days)
        rolling_high = result["high"].rolling(window=min(252, len(result))).max()
        rolling_low = result["low"].rolling(window=min(252, len(result))).min()
        result["dist_52w_high"] = (result["close"] - rolling_high) / rolling_high
        result["dist_52w_low"] = (result["close"] - rolling_low) / rolling_low

        # Intraday range
        result["intraday_range"] = (result["high"] - result["low"]) / result["open"]

        logger.debug("Computed features", columns=len(result.columns), rows=len(result))
        return result

    def compute_subset(self, df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
        """Compute only specified features."""
        full = self.compute_all(df)
        available = [f for f in features if f in full.columns]
        base_cols = ["open", "high", "low", "close", "volume"]
        return full[base_cols + available]
