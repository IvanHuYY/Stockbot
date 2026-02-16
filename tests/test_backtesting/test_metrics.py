"""Tests for performance metrics."""

import numpy as np
import pandas as pd

from stockbot.backtesting.metrics import PerformanceMetrics


def test_compute_basic_metrics():
    dates = pd.date_range("2024-01-01", periods=252, freq="B")
    # Simulate 10% annual return with some noise
    returns = np.random.normal(0.0004, 0.01, 252)
    prices = 100000 * np.cumprod(1 + returns)
    equity = pd.Series(prices, index=dates)

    trades = [
        {"pnl": 500, "side": "sell"},
        {"pnl": -200, "side": "sell"},
        {"pnl": 300, "side": "sell"},
        {"pnl": -100, "side": "sell"},
        {"pnl": 400, "side": "sell"},
    ]

    metrics = PerformanceMetrics.compute(equity, trades)

    assert "total_return" in metrics
    assert "sharpe_ratio" in metrics
    assert "max_drawdown" in metrics
    assert "win_rate" in metrics
    assert metrics["num_trades"] == 5
    assert metrics["win_rate"] == 0.6  # 3 wins out of 5


def test_compute_empty():
    equity = pd.Series(dtype=float)
    metrics = PerformanceMetrics.compute(equity, [])
    assert metrics["total_return"] == 0.0
    assert metrics["num_trades"] == 0


def test_compute_no_trades():
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    equity = pd.Series(np.linspace(100000, 110000, 10), index=dates)
    metrics = PerformanceMetrics.compute(equity, [])

    assert metrics["total_return"] > 0
    assert metrics["num_trades"] == 0
    assert metrics["win_rate"] == 0


def test_max_drawdown():
    # Create a series with a known drawdown
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    values = [100, 110, 105, 95, 90, 100, 110, 108, 115, 120]
    equity = pd.Series(values, index=dates, dtype=float)
    metrics = PerformanceMetrics.compute(equity, [])

    # Max drawdown should be from 110 to 90 = -18.18%
    assert metrics["max_drawdown"] < -0.15
