"""Position management - track holdings and P&L."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from alpaca.trading import TradingClient
    from alpaca.trading.models import Order

logger = structlog.get_logger()


@dataclass
class PositionInfo:
    symbol: str
    qty: float
    side: str
    market_value: float
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    cost_basis: float


class PositionManager:
    def __init__(self, trading_client: TradingClient) -> None:
        self._client = trading_client

    def get_all_positions(self) -> list[PositionInfo]:
        """Get all open positions."""
        positions = self._client.get_all_positions()
        return [self._to_position_info(p) for p in positions]

    def get_position(self, symbol: str) -> PositionInfo | None:
        """Get position for a specific symbol, or None if not held."""
        try:
            position = self._client.get_open_position(symbol)
            return self._to_position_info(position)
        except Exception:
            return None

    def close_position(self, symbol: str) -> Order:
        """Close an entire position for a symbol."""
        order = self._client.close_position(symbol)
        logger.info("Position closed", symbol=symbol, order_id=str(order.id))
        return order

    def close_all_positions(self) -> list:
        """Close all open positions."""
        results = self._client.close_all_positions()
        logger.info("All positions closed", count=len(results))
        return results

    def get_portfolio_value(self) -> float:
        """Total market value of all positions."""
        positions = self._client.get_all_positions()
        return sum(float(p.market_value) for p in positions)

    def get_unrealized_pnl(self) -> float:
        """Total unrealized P&L across all positions."""
        positions = self._client.get_all_positions()
        return sum(float(p.unrealized_pl) for p in positions)

    @staticmethod
    def _to_position_info(position) -> PositionInfo:
        return PositionInfo(
            symbol=position.symbol,
            qty=float(position.qty),
            side=position.side.value if hasattr(position.side, "value") else str(position.side),
            market_value=float(position.market_value),
            avg_entry_price=float(position.avg_entry_price),
            current_price=float(position.current_price),
            unrealized_pnl=float(position.unrealized_pl),
            unrealized_pnl_pct=float(position.unrealized_plpc),
            cost_basis=float(position.cost_basis),
        )
