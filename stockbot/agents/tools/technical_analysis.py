"""Technical analysis tools available to the Market Analyst agent."""

from __future__ import annotations

import json

import pandas as pd
import pandas_ta as ta
from langchain_core.tools import tool


@tool
def get_technical_indicators(ohlcv_json: str) -> str:
    """Compute technical indicators (RSI, MACD, Bollinger Bands, SMA, EMA, ATR, OBV)
    from OHLCV data. Input: JSON string of OHLCV data with columns
    open, high, low, close, volume."""
    data = json.loads(ohlcv_json)
    df = pd.DataFrame(data)

    if df.empty or len(df) < 2:
        return json.dumps({"error": "Insufficient data"})

    indicators = {}

    # RSI
    rsi = ta.rsi(df["close"], length=14)
    if rsi is not None:
        indicators["rsi_14"] = round(float(rsi.iloc[-1]), 2) if not rsi.empty else None

    rsi7 = ta.rsi(df["close"], length=7)
    if rsi7 is not None:
        indicators["rsi_7"] = round(float(rsi7.iloc[-1]), 2) if not rsi7.empty else None

    # MACD
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        last = macd.iloc[-1]
        indicators["macd"] = round(float(last.iloc[0]), 4)
        indicators["macd_signal"] = round(float(last.iloc[2]), 4)
        indicators["macd_histogram"] = round(float(last.iloc[1]), 4)
        indicators["macd_trend"] = "bullish" if last.iloc[1] > 0 else "bearish"

    # Bollinger Bands
    bbands = ta.bbands(df["close"], length=20, std=2.0)
    if bbands is not None and not bbands.empty:
        last_bb = bbands.iloc[-1]
        last_close = float(df["close"].iloc[-1])
        indicators["bb_upper"] = round(float(last_bb.iloc[0]), 2)
        indicators["bb_middle"] = round(float(last_bb.iloc[1]), 2)
        indicators["bb_lower"] = round(float(last_bb.iloc[2]), 2)
        bb_width = float(last_bb.iloc[0]) - float(last_bb.iloc[2])
        indicators["bb_position"] = round(
            (last_close - float(last_bb.iloc[2])) / bb_width if bb_width > 0 else 0.5, 2
        )

    # Moving Averages
    for length in [20, 50, 200]:
        sma = ta.sma(df["close"], length=length)
        if sma is not None and not sma.empty and pd.notna(sma.iloc[-1]):
            indicators[f"sma_{length}"] = round(float(sma.iloc[-1]), 2)

    for length in [9, 21]:
        ema = ta.ema(df["close"], length=length)
        if ema is not None and not ema.empty and pd.notna(ema.iloc[-1]):
            indicators[f"ema_{length}"] = round(float(ema.iloc[-1]), 2)

    # ATR
    atr = ta.atr(df["high"], df["low"], df["close"], length=14)
    if atr is not None and not atr.empty and pd.notna(atr.iloc[-1]):
        indicators["atr_14"] = round(float(atr.iloc[-1]), 2)

    # OBV
    obv = ta.obv(df["close"], df["volume"])
    if obv is not None and not obv.empty:
        indicators["obv"] = int(obv.iloc[-1])
        indicators["obv_trend"] = "up" if len(obv) > 5 and obv.iloc[-1] > obv.iloc[-5] else "down"

    # Current price info
    indicators["current_price"] = round(float(df["close"].iloc[-1]), 2)
    indicators["price_change_1d"] = round(float(df["close"].pct_change().iloc[-1] * 100), 2)

    return json.dumps(indicators)


@tool
def get_support_resistance(ohlcv_json: str) -> str:
    """Calculate support and resistance levels from recent price action.
    Input: JSON string of OHLCV data."""
    data = json.loads(ohlcv_json)
    df = pd.DataFrame(data)

    if df.empty or len(df) < 20:
        return json.dumps({"error": "Need at least 20 bars"})

    recent = df.tail(60) if len(df) >= 60 else df

    # Simple pivot-based support/resistance
    high = float(recent["high"].max())
    low = float(recent["low"].min())
    close = float(recent["close"].iloc[-1])
    pivot = (high + low + close) / 3

    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    # Find local minima/maxima as key levels
    rolling_high = recent["high"].rolling(window=5, center=True).max()
    rolling_low = recent["low"].rolling(window=5, center=True).min()

    resistance_levels = sorted(
        set(round(float(v), 2) for v in rolling_high.dropna().unique() if v > close), key=float
    )[:3]

    support_levels = sorted(
        set(round(float(v), 2) for v in rolling_low.dropna().unique() if v < close),
        key=float,
        reverse=True,
    )[:3]

    return json.dumps({
        "pivot": round(pivot, 2),
        "resistance_1": round(r1, 2),
        "resistance_2": round(r2, 2),
        "support_1": round(s1, 2),
        "support_2": round(s2, 2),
        "key_resistance_levels": resistance_levels[:3],
        "key_support_levels": support_levels[:3],
        "current_price": round(close, 2),
    })
