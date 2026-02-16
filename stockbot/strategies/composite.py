"""Composite strategy combining multiple signal sources."""

from __future__ import annotations

import pandas as pd

from stockbot.strategies.base import BaseStrategy, Signal
from stockbot.strategies.mean_reversion import MeanReversionStrategy
from stockbot.strategies.momentum import MomentumStrategy


class CompositeStrategy(BaseStrategy):
    """Combines momentum and mean reversion signals with configurable weights."""

    def __init__(
        self,
        momentum_weight: float = 0.6,
        mean_reversion_weight: float = 0.4,
    ) -> None:
        self._momentum = MomentumStrategy()
        self._mean_reversion = MeanReversionStrategy()
        self._momentum_weight = momentum_weight
        self._mean_reversion_weight = mean_reversion_weight

    @property
    def name(self) -> str:
        return "composite"

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        momentum_signals = {s.symbol: s for s in self._momentum.generate_signals(data)}
        mr_signals = {s.symbol: s for s in self._mean_reversion.generate_signals(data)}

        signals = []
        for symbol in data:
            mom = momentum_signals.get(symbol)
            mr = mr_signals.get(symbol)

            if mom is None and mr is None:
                signals.append(Signal(symbol=symbol, action="hold", strength=0.0, reason="No data"))
                continue

            # Combine scores
            mom_score = 0.0
            mr_score = 0.0
            reasons = []

            if mom:
                mom_score = mom.strength * (1 if mom.action == "buy" else -1 if mom.action == "sell" else 0)
                if mom.action != "hold":
                    reasons.append(f"Momentum: {mom.reason}")

            if mr:
                mr_score = mr.strength * (1 if mr.action == "buy" else -1 if mr.action == "sell" else 0)
                if mr.action != "hold":
                    reasons.append(f"MeanRev: {mr.reason}")

            combined = (
                mom_score * self._momentum_weight + mr_score * self._mean_reversion_weight
            )
            combined = max(-1.0, min(1.0, combined))

            if combined > 0.25:
                action = "buy"
            elif combined < -0.25:
                action = "sell"
            else:
                action = "hold"

            signals.append(Signal(
                symbol=symbol,
                action=action,
                strength=abs(combined),
                reason="; ".join(reasons) if reasons else "Signals balanced, holding",
            ))

        return signals
