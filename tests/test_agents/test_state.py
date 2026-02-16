"""Tests for agent state definitions."""

from stockbot.agents.state import (
    AgentState,
    MarketAnalysis,
    RiskAssessment,
    TradeDecision,
)


def test_market_analysis_creation():
    analysis = MarketAnalysis(
        symbol="AAPL",
        technical_signals={"rsi_14": 35},
        sentiment_score=0.5,
        support_level=145.0,
        resistance_level=160.0,
        recommendation="buy",
        confidence=0.75,
        reasoning="Strong momentum with oversold RSI",
    )
    assert analysis["symbol"] == "AAPL"
    assert analysis["recommendation"] == "buy"
    assert analysis["confidence"] == 0.75


def test_risk_assessment_creation():
    assessment = RiskAssessment(
        symbol="AAPL",
        approved=True,
        max_position_size=5000.0,
        suggested_stop_loss=145.0,
        suggested_take_profit=165.0,
        risk_reward_ratio=2.5,
        portfolio_risk_after=0.15,
        reasoning="Within risk limits",
    )
    assert assessment["approved"] is True
    assert assessment["risk_reward_ratio"] == 2.5


def test_trade_decision_creation():
    decision = TradeDecision(
        action="buy",
        symbol="AAPL",
        quantity=10,
        order_type="bracket",
        limit_price=None,
        stop_loss=145.0,
        take_profit=165.0,
        reasoning="Approved by risk manager",
    )
    assert decision["action"] == "buy"
    assert decision["quantity"] == 10
    assert decision["order_type"] == "bracket"
