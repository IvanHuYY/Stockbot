"""Tests for the account manager."""

from stockbot.broker.account import AccountManager


def test_get_account_info(mock_trading_client):
    manager = AccountManager(mock_trading_client)
    info = manager.get_account_info()

    assert info.equity == 100000.0
    assert info.cash == 50000.0
    assert info.buying_power == 100000.0
    assert info.daily_pnl == 1000.0  # 100000 - 99000
    assert abs(info.daily_pnl_pct - (1000.0 / 99000.0)) < 0.0001


def test_get_buying_power(mock_trading_client):
    manager = AccountManager(mock_trading_client)
    bp = manager.get_buying_power()
    assert bp == 100000.0


def test_is_day_trade_restricted(mock_trading_client):
    manager = AccountManager(mock_trading_client)
    assert not manager.is_day_trade_restricted()
