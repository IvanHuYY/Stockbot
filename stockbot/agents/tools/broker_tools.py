"""Broker interaction tools for the Portfolio Manager agent."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

# These tools are created as closures that capture the broker client.
# The factory functions below return tool instances bound to a specific broker.


def create_broker_tools(broker: Any) -> list:
    """Create broker tools bound to a specific AlpacaClient instance."""

    @tool
    def get_current_positions() -> str:
        """Get all current portfolio positions with P&L details."""
        positions = broker.positions.get_all_positions()
        return json.dumps([
            {
                "symbol": p.symbol,
                "qty": p.qty,
                "side": p.side,
                "market_value": p.market_value,
                "avg_entry_price": p.avg_entry_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
                "unrealized_pnl_pct": p.unrealized_pnl_pct,
            }
            for p in positions
        ])

    @tool
    def get_buying_power() -> str:
        """Get available buying power for new trades."""
        info = broker.account.get_account_info()
        return json.dumps({
            "buying_power": info.buying_power,
            "cash": info.cash,
            "equity": info.equity,
            "portfolio_value": info.portfolio_value,
        })

    @tool
    def check_existing_orders() -> str:
        """Check for any open/pending orders that might conflict with new trades."""
        orders = broker.orders.list_open_orders()
        return json.dumps([
            {
                "order_id": str(o.id),
                "symbol": o.symbol,
                "side": str(o.side),
                "qty": str(o.qty),
                "type": str(o.type),
                "status": str(o.status),
            }
            for o in orders
        ])

    return [get_current_positions, get_buying_power, check_existing_orders]
