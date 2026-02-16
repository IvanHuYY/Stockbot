"""Shared agent state definition for the LangGraph trading pipeline."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from operator import add


class MarketAnalysis(TypedDict):
    symbol: str
    technical_signals: dict[str, Any]
    sentiment_score: float  # -1.0 to 1.0
    support_level: float
    resistance_level: float
    recommendation: Literal["strong_buy", "buy", "hold", "sell", "strong_sell"]
    confidence: float  # 0.0 to 1.0
    reasoning: str


class RiskAssessment(TypedDict):
    symbol: str
    approved: bool
    max_position_size: float  # in dollars
    suggested_stop_loss: float
    suggested_take_profit: float
    risk_reward_ratio: float
    portfolio_risk_after: float
    reasoning: str


class TradeDecision(TypedDict):
    action: Literal["buy", "sell", "hold"]
    symbol: str
    quantity: int
    order_type: Literal["market", "limit", "bracket"]
    limit_price: float | None
    stop_loss: float | None
    take_profit: float | None
    reasoning: str


class ExecutionResult(TypedDict):
    symbol: str
    order_id: str
    status: str  # "submitted", "failed"
    error: str


class AgentState(TypedDict):
    """Shared state passed through the LangGraph pipeline."""

    messages: Annotated[list, add]

    # Input
    symbols_to_analyze: list[str]

    # Data (populated by data_loader)
    market_data: dict[str, Any]  # symbol -> DataFrame-like data
    news_data: list[dict[str, Any]]
    account_info: dict[str, Any]
    current_positions: list[dict[str, Any]]

    # Agent outputs
    analyses: list[MarketAnalysis]
    risk_assessments: list[RiskAssessment]
    trade_decisions: list[TradeDecision]
    execution_results: list[ExecutionResult]

    # Metadata
    cycle_id: str
    cycle_timestamp: str
