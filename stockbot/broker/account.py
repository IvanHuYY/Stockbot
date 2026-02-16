"""Account management - buying power, equity, margin info."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from alpaca.trading import TradingClient

logger = structlog.get_logger()


@dataclass
class AccountInfo:
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    daily_pnl: float
    daily_pnl_pct: float


class AccountManager:
    def __init__(self, trading_client: TradingClient) -> None:
        self._client = trading_client

    def get_account_info(self) -> AccountInfo:
        """Get current account information."""
        account = self._client.get_account()
        equity = float(account.equity)
        last_equity = float(account.last_equity)
        daily_pnl = equity - last_equity
        daily_pnl_pct = (daily_pnl / last_equity) if last_equity > 0 else 0.0

        return AccountInfo(
            equity=equity,
            cash=float(account.cash),
            buying_power=float(account.buying_power),
            portfolio_value=float(account.portfolio_value or equity),
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
        )

    def get_buying_power(self) -> float:
        """Get available buying power."""
        account = self._client.get_account()
        return float(account.buying_power)

    def is_day_trade_restricted(self) -> bool:
        """Check if account is flagged as pattern day trader."""
        account = self._client.get_account()
        return bool(account.pattern_day_trader)
