"""Order simulator for backtesting - simulates fills, slippage, commissions."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class SimulatedOrder:
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    order_type: Literal["market", "limit"]
    limit_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


@dataclass
class SimulatedFill:
    symbol: str
    side: str
    quantity: int
    fill_price: float
    commission: float
    slippage: float
    timestamp: datetime


@dataclass
class SimulatedPosition:
    symbol: str
    quantity: int
    avg_entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    entry_time: datetime | None = None


@dataclass
class SimulatedPortfolio:
    cash: float
    initial_capital: float
    positions: dict[str, SimulatedPosition] = field(default_factory=dict)
    trades: list[SimulatedFill] = field(default_factory=list)
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)

    @property
    def total_value(self) -> float:
        return self.cash + sum(
            p.quantity * p.avg_entry_price for p in self.positions.values()
        )


class OrderSimulator:
    """Simulates order execution against historical data."""

    def __init__(
        self,
        commission_per_trade: float = 0.0,
        slippage_bps: float = 5.0,
    ) -> None:
        self._commission = commission_per_trade
        self._slippage_bps = slippage_bps

    def fill_market_order(
        self,
        order: SimulatedOrder,
        bar_open: float,
        timestamp: datetime,
    ) -> SimulatedFill:
        """Simulate a market order fill at bar open + slippage."""
        slippage = self._calculate_slippage(bar_open, order.side)
        fill_price = bar_open + slippage

        return SimulatedFill(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            fill_price=round(fill_price, 2),
            commission=self._commission,
            slippage=round(slippage, 4),
            timestamp=timestamp,
        )

    def check_stop_loss(
        self,
        position: SimulatedPosition,
        bar_low: float,
        bar_high: float,
        timestamp: datetime,
    ) -> SimulatedFill | None:
        """Check if a stop-loss was triggered during this bar."""
        if position.stop_loss is None:
            return None

        if position.quantity > 0 and bar_low <= position.stop_loss:
            return SimulatedFill(
                symbol=position.symbol,
                side="sell",
                quantity=position.quantity,
                fill_price=position.stop_loss,
                commission=self._commission,
                slippage=0,
                timestamp=timestamp,
            )
        return None

    def check_take_profit(
        self,
        position: SimulatedPosition,
        bar_high: float,
        timestamp: datetime,
    ) -> SimulatedFill | None:
        """Check if take-profit was hit during this bar."""
        if position.take_profit is None:
            return None

        if position.quantity > 0 and bar_high >= position.take_profit:
            return SimulatedFill(
                symbol=position.symbol,
                side="sell",
                quantity=position.quantity,
                fill_price=position.take_profit,
                commission=self._commission,
                slippage=0,
                timestamp=timestamp,
            )
        return None

    def _calculate_slippage(self, price: float, side: str) -> float:
        """Calculate slippage based on configured model."""
        base_slippage = price * (self._slippage_bps / 10000)
        # Add small randomness
        jitter = random.uniform(0.8, 1.2)
        slippage = base_slippage * jitter
        # Slippage is adverse: higher for buys, lower for sells
        return slippage if side == "buy" else -slippage
