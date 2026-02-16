"""Database models for trades, agent decisions, and equity snapshots."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Trade(SQLModel, table=True):
    __tablename__ = "trades"

    id: int | None = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    side: str  # "buy" or "sell"
    quantity: float
    price: float | None = None
    order_type: str  # "market", "limit", "bracket"
    order_id: str = Field(index=True)
    status: str  # "submitted", "filled", "cancelled", "failed"
    stop_loss: float | None = None
    take_profit: float | None = None
    cycle_id: str = Field(index=True)
    reasoning: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentDecision(SQLModel, table=True):
    __tablename__ = "agent_decisions"

    id: int | None = Field(default=None, primary_key=True)
    cycle_id: str = Field(index=True)
    agent_name: str  # "market_analyst", "risk_manager", "portfolio_manager"
    symbol: str = Field(index=True)
    input_data: str = ""  # JSON
    output_data: str = ""  # JSON
    reasoning: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EquitySnapshot(SQLModel, table=True):
    __tablename__ = "equity_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    portfolio_value: float
    cash: float
    unrealized_pnl: float
    realized_pnl_today: float = 0.0
    num_positions: int = 0
