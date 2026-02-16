"""Mean reversion strategy."""

from __future__ import annotations

import pandas as pd

from stockbot.strategies.base import BaseStrategy, Signal


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands, RSI, and Z-score."""

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        rsi_entry_low: float = 25,
        rsi_entry_high: float = 75,
        z_score_entry: float = 2.0,
        z_score_exit: float = 0.5,
    ) -> None:
        self._bb_period = bb_period
        self._bb_std = bb_std
        self._rsi_entry_low = rsi_entry_low
        self._rsi_entry_high = rsi_entry_high
        self._z_score_entry = z_score_entry
        self._z_score_exit = z_score_exit

    @property
    def name(self) -> str:
        return "mean_reversion"

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        signals = []

        for symbol, df in data.items():
            if df.empty or len(df) < self._bb_period + 5:
                signals.append(Signal(symbol=symbol, action="hold", strength=0.0, reason="Insufficient data"))
                continue

            df = self._ensure_indicators(df)
            last = df.iloc[-1]

            score = 0.0
            reasons = []

            # Bollinger Band signal
            bb_lower = last.get(f"BBL_{self._bb_period}_{self._bb_std}")
            bb_upper = last.get(f"BBU_{self._bb_period}_{self._bb_std}")
            close = last.get("close", 0)

            if bb_lower is not None and bb_upper is not None and pd.notna(bb_lower) and pd.notna(bb_upper):
                if close < bb_lower:
                    score += 0.4
                    reasons.append("Price below lower Bollinger Band (oversold)")
                elif close > bb_upper:
                    score -= 0.4
                    reasons.append("Price above upper Bollinger Band (overbought)")

            # RSI mean reversion
            rsi = last.get("rsi_14")
            if rsi is not None and pd.notna(rsi):
                if rsi < self._rsi_entry_low:
                    score += 0.3
                    reasons.append(f"RSI extreme low ({rsi:.0f})")
                elif rsi > self._rsi_entry_high:
                    score -= 0.3
                    reasons.append(f"RSI extreme high ({rsi:.0f})")

            # Z-score of price relative to 20-day mean
            sma = last.get(f"sma_{self._bb_period}")
            if sma is not None and pd.notna(sma) and close > 0:
                std = df["close"].tail(self._bb_period).std()
                if std > 0:
                    z_score = (close - sma) / std
                    if z_score < -self._z_score_entry:
                        score += 0.3
                        reasons.append(f"Z-score extremely low ({z_score:.1f})")
                    elif z_score > self._z_score_entry:
                        score -= 0.3
                        reasons.append(f"Z-score extremely high ({z_score:.1f})")

            # Convert score to signal
            score = max(-1.0, min(1.0, score))
            if score > 0.3:
                action = "buy"
            elif score < -0.3:
                action = "sell"
            else:
                action = "hold"

            signals.append(Signal(
                symbol=symbol,
                action=action,
                strength=abs(score),
                reason="; ".join(reasons) if reasons else "Price near mean, no reversion signal",
            ))

        return signals
