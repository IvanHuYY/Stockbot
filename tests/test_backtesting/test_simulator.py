"""Tests for the order simulator."""

from datetime import datetime

from stockbot.backtesting.simulator import (
    OrderSimulator,
    SimulatedOrder,
    SimulatedPosition,
)


def test_fill_market_order_buy():
    sim = OrderSimulator(commission_per_trade=1.0, slippage_bps=10.0)
    order = SimulatedOrder(symbol="AAPL", side="buy", quantity=10, order_type="market")
    fill = sim.fill_market_order(order, bar_open=150.0, timestamp=datetime(2024, 1, 2))

    assert fill.symbol == "AAPL"
    assert fill.quantity == 10
    assert fill.commission == 1.0
    # Buy slippage should increase price
    assert fill.fill_price >= 150.0


def test_fill_market_order_sell():
    sim = OrderSimulator(commission_per_trade=0.0, slippage_bps=10.0)
    order = SimulatedOrder(symbol="AAPL", side="sell", quantity=5, order_type="market")
    fill = sim.fill_market_order(order, bar_open=150.0, timestamp=datetime(2024, 1, 2))

    assert fill.quantity == 5
    # Sell slippage should decrease price
    assert fill.fill_price <= 150.0


def test_check_stop_loss_triggered():
    sim = OrderSimulator()
    position = SimulatedPosition(
        symbol="AAPL", quantity=10, avg_entry_price=150.0, stop_loss=145.0
    )
    fill = sim.check_stop_loss(position, bar_low=144.0, bar_high=151.0, timestamp=datetime(2024, 1, 2))

    assert fill is not None
    assert fill.fill_price == 145.0
    assert fill.side == "sell"


def test_check_stop_loss_not_triggered():
    sim = OrderSimulator()
    position = SimulatedPosition(
        symbol="AAPL", quantity=10, avg_entry_price=150.0, stop_loss=145.0
    )
    fill = sim.check_stop_loss(position, bar_low=146.0, bar_high=155.0, timestamp=datetime(2024, 1, 2))

    assert fill is None


def test_check_take_profit_triggered():
    sim = OrderSimulator()
    position = SimulatedPosition(
        symbol="AAPL", quantity=10, avg_entry_price=150.0, take_profit=160.0
    )
    fill = sim.check_take_profit(position, bar_high=161.0, timestamp=datetime(2024, 1, 2))

    assert fill is not None
    assert fill.fill_price == 160.0
