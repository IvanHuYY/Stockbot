"""Tests for feature engineering."""

from stockbot.data.features import FeatureEngineer


def test_compute_all(sample_ohlcv):
    eng = FeatureEngineer()
    result = eng.compute_all(sample_ohlcv)

    # Should have original columns plus indicators
    assert "rsi_14" in result.columns
    assert "sma_20" in result.columns
    assert "ema_9" in result.columns
    assert "atr_14" in result.columns
    assert "obv" in result.columns
    assert "price_change_1d" in result.columns
    assert "volume_sma_ratio" in result.columns
    assert "intraday_range" in result.columns

    # Should have same number of rows
    assert len(result) == len(sample_ohlcv)


def test_compute_all_empty():
    import pandas as pd

    eng = FeatureEngineer()
    result = eng.compute_all(pd.DataFrame())
    assert result.empty


def test_compute_subset(sample_ohlcv):
    eng = FeatureEngineer()
    result = eng.compute_subset(sample_ohlcv, ["rsi_14", "sma_20"])

    assert "rsi_14" in result.columns
    assert "sma_20" in result.columns
    assert "open" in result.columns  # base cols always included
    assert "close" in result.columns
