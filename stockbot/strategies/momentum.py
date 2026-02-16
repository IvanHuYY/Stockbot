"""Momentum / trend-following strategy."""

from __future__ import annotations

import pandas as pd

from stockbot.strategies.base import BaseStrategy, Signal


class MomentumStrategy(BaseStrategy):
    """Trend-following strategy using RSI, MACD, and moving average crossovers."""

    def __init__(
        self,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        sma_short: int = 20,
        sma_long: int = 50,
        volume_threshold: float = 1.5,
    ) -> None:
        self._rsi_oversold = rsi_oversold
        self._rsi_overbought = rsi_overbought
        self._sma_short = sma_short
        self._sma_long = sma_long
        self._volume_threshold = volume_threshold

    @property
    def name(self) -> str:
        return "momentum"

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> list[Signal]:
        signals = []

        for symbol, df in data.items():
            if df.empty or len(df) < self._sma_long:
                signals.append(Signal(symbol=symbol, action="hold", strength=0.0, reason="Insufficient data"))
                continue

            df = self._ensure_indicators(df)
            last = df.iloc[-1]

            score = 0.0
            reasons = []

            # RSI signal
            rsi = last.get("rsi_14")
            if rsi is not None and pd.notna(rsi):
                if rsi < self._rsi_oversold:
                    score += 0.3
                    reasons.append(f"RSI oversold ({rsi:.0f})")
                elif rsi > self._rsi_overbought:
                    score -= 0.3
                    reasons.append(f"RSI overbought ({rsi:.0f})")

            # MACD signal
            macd_hist = last.get("MACDh_12_26_9")
            if macd_hist is not None and pd.notna(macd_hist):
                prev_hist = df.iloc[-2].get("MACDh_12_26_9") if len(df) > 1 else None
                if prev_hist is not None and pd.notna(prev_hist):
                    if macd_hist > 0 and prev_hist <= 0:
                        score += 0.3
                        reasons.append("MACD bullish crossover")
                    elif macd_hist < 0 and prev_hist >= 0:
                        score -= 0.3
                        reasons.append("MACD bearish crossover")

            # SMA crossover
            sma_short = last.get(f"sma_{self._sma_short}")
            sma_long = last.get(f"sma_{self._sma_long}")
            if sma_short is not None and sma_long is not None and pd.notna(sma_short) and pd.notna(sma_long):
                if sma_short > sma_long:
                    score += 0.2
                    reasons.append(f"SMA{self._sma_short} > SMA{self._sma_long}")
                else:
                    score -= 0.2
                    reasons.append(f"SMA{self._sma_short} < SMA{self._sma_long}")

            # Volume confirmation
            vol_ratio = last.get("volume_sma_ratio")
            if vol_ratio is not None and pd.notna(vol_ratio) and vol_ratio > self._volume_threshold:
                score *= 1.2  # Amplify signal on high volume
                reasons.append(f"High volume ({vol_ratio:.1f}x avg)")

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
                reason="; ".join(reasons) if reasons else "No strong signals",
            ))

        return signals
