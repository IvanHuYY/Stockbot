"""Order management - submit, cancel, and track orders."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import (
    LimitOrderRequest,
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)

if TYPE_CHECKING:
    from alpaca.trading import TradingClient
    from alpaca.trading.models import Order

logger = structlog.get_logger()


class OrderManager:
    def __init__(self, trading_client: TradingClient) -> None:
        self._client = trading_client

    def submit_market_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        time_in_force: TimeInForce = TimeInForce.DAY,
    ) -> Order:
        """Submit a market order."""
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=time_in_force,
        )
        order = self._client.submit_order(request)
        logger.info(
            "Market order submitted",
            symbol=symbol,
            side=side,
            qty=qty,
            order_id=str(order.id),
        )
        return order

    def submit_limit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        limit_price: float,
        time_in_force: TimeInForce = TimeInForce.DAY,
    ) -> Order:
        """Submit a limit order."""
        request = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=time_in_force,
            limit_price=limit_price,
        )
        order = self._client.submit_order(request)
        logger.info(
            "Limit order submitted",
            symbol=symbol,
            side=side,
            qty=qty,
            limit_price=limit_price,
            order_id=str(order.id),
        )
        return order

    def submit_bracket_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        take_profit: float,
        stop_loss: float,
        time_in_force: TimeInForce = TimeInForce.DAY,
    ) -> Order:
        """Submit a bracket order with take-profit and stop-loss."""
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=time_in_force,
            order_class="bracket",
            take_profit=TakeProfitRequest(limit_price=take_profit),
            stop_loss=StopLossRequest(stop_price=stop_loss),
        )
        order = self._client.submit_order(request)
        logger.info(
            "Bracket order submitted",
            symbol=symbol,
            side=side,
            qty=qty,
            take_profit=take_profit,
            stop_loss=stop_loss,
            order_id=str(order.id),
        )
        return order

    def cancel_order(self, order_id: str) -> None:
        """Cancel an open order."""
        self._client.cancel_order_by_id(order_id)
        logger.info("Order cancelled", order_id=order_id)

    def cancel_all_orders(self) -> None:
        """Cancel all open orders."""
        self._client.cancel_orders()
        logger.info("All orders cancelled")

    def get_order(self, order_id: str) -> Order:
        """Get order details by ID."""
        return self._client.get_order_by_id(order_id)

    def list_open_orders(self) -> list[Order]:
        """List all open orders."""
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus

        request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        return self._client.get_orders(request)
