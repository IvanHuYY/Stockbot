"""Base strategy interface for rule-based signal generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass
class Signal:
    symbol: str
    action: Literal["buy", "sell", "hold"]
    strength: float  # 0.0 to 1.0
    reason: str


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""
        ...

    @abstractmethod
    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        """Generate trading signals from OHLCV data.

        Args:
            data: dict mapping symbol -> DataFrame with OHLCV + indicators

        Returns:
            List of Signal objects for each symbol
        """
        ...

    def _ensure_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute indicators if not already present."""
        from stockbot.data.features import FeatureEngineer

        if "rsi_14" not in df.columns:
            eng = FeatureEngineer()
            return eng.compute_all(df)
        return df
