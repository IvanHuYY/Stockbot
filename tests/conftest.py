"""Shared test fixtures."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="B", tz=timezone.utc)
    base_price = 150.0
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * np.cumprod(1 + returns)

    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.uniform(-0.005, 0.005, 100)),
            "high": prices * (1 + np.random.uniform(0.005, 0.02, 100)),
            "low": prices * (1 - np.random.uniform(0.005, 0.02, 100)),
            "close": prices,
            "volume": np.random.randint(1_000_000, 10_000_000, 100),
            "vwap": prices,
            "trade_count": np.random.randint(1000, 50000, 100),
        },
        index=dates,
    )
    df.index.name = "timestamp"
    return df


@pytest.fixture
def mock_trading_client():
    """Mock Alpaca TradingClient."""
    client = MagicMock()

    # Mock account
    account = MagicMock()
    account.equity = "100000.00"
    account.cash = "50000.00"
    account.buying_power = "100000.00"
    account.portfolio_value = "100000.00"
    account.last_equity = "99000.00"
    account.pattern_day_trader = False
    client.get_account.return_value = account

    # Mock positions
    client.get_all_positions.return_value = []

    # Mock orders
    client.get_orders.return_value = []

    return client


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from config.settings import Settings

    return Settings(
        alpaca_api_key="test_key",
        alpaca_secret_key="test_secret",
        paper_trading=True,
        llm_provider="anthropic",
        anthropic_api_key="test_key",
        llm_model="claude-sonnet-4-20250514",
    )
