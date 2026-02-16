"""Tests for DuckDB market data storage."""

import os
import tempfile

import pytest

from stockbot.data.storage import MarketDataStore


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.duckdb")
    s = MarketDataStore(db_path)
    yield s
    s.close()


def test_save_and_load_bars(store, sample_ohlcv):
    rows = store.save_bars("AAPL", "1day", sample_ohlcv)
    assert rows == len(sample_ohlcv)

    loaded = store.load_bars("AAPL", "1day")
    assert len(loaded) == len(sample_ohlcv)
    assert "close" in loaded.columns


def test_get_available_range(store, sample_ohlcv):
    store.save_bars("AAPL", "1day", sample_ohlcv)
    result = store.get_available_range("AAPL", "1day")

    assert result is not None
    assert result[0] is not None
    assert result[1] is not None


def test_get_stored_symbols(store, sample_ohlcv):
    store.save_bars("AAPL", "1day", sample_ohlcv)
    store.save_bars("MSFT", "1day", sample_ohlcv)

    symbols = store.get_stored_symbols()
    assert "AAPL" in symbols
    assert "MSFT" in symbols


def test_empty_dataframe(store):
    import pandas as pd

    rows = store.save_bars("AAPL", "1day", pd.DataFrame())
    assert rows == 0


def test_load_nonexistent(store):
    loaded = store.load_bars("NONEXIST", "1day")
    assert loaded.empty
