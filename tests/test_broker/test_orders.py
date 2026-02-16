"""Tests for the order manager."""

from unittest.mock import MagicMock

from stockbot.broker.orders import OrderManager


def test_submit_market_order(mock_trading_client):
    mock_order = MagicMock()
    mock_order.id = "test-order-123"
    mock_trading_client.submit_order.return_value = mock_order

    manager = OrderManager(mock_trading_client)
    order = manager.submit_market_order("AAPL", 10, "buy")

    assert order.id == "test-order-123"
    mock_trading_client.submit_order.assert_called_once()


def test_submit_limit_order(mock_trading_client):
    mock_order = MagicMock()
    mock_order.id = "test-order-456"
    mock_trading_client.submit_order.return_value = mock_order

    manager = OrderManager(mock_trading_client)
    order = manager.submit_limit_order("AAPL", 10, "buy", limit_price=150.0)

    assert order.id == "test-order-456"
    mock_trading_client.submit_order.assert_called_once()


def test_cancel_order(mock_trading_client):
    manager = OrderManager(mock_trading_client)
    manager.cancel_order("test-order-123")
    mock_trading_client.cancel_order_by_id.assert_called_once_with("test-order-123")


def test_list_open_orders(mock_trading_client):
    mock_trading_client.get_orders.return_value = []
    manager = OrderManager(mock_trading_client)
    orders = manager.list_open_orders()
    assert orders == []
