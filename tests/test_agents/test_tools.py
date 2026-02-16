"""Tests for agent tools."""

import json

from stockbot.agents.tools.sentiment import analyze_news_sentiment
from stockbot.agents.tools.risk_tools import (
    calculate_position_size,
    calculate_stop_loss,
    get_portfolio_exposure,
)


def test_analyze_news_sentiment_positive():
    articles = [
        {"title": "Stock surges to record high", "summary": "Strong growth and profit beat expectations"},
    ]
    result = json.loads(analyze_news_sentiment.invoke(json.dumps(articles)))
    assert result["overall_sentiment"] > 0
    assert result["article_count"] == 1


def test_analyze_news_sentiment_negative():
    articles = [
        {"title": "Stock plunges on weak earnings", "summary": "Loss and decline concern investors"},
    ]
    result = json.loads(analyze_news_sentiment.invoke(json.dumps(articles)))
    assert result["overall_sentiment"] < 0


def test_analyze_news_sentiment_empty():
    result = json.loads(analyze_news_sentiment.invoke(json.dumps([])))
    assert result["overall_sentiment"] == 0
    assert result["article_count"] == 0


def test_calculate_position_size():
    result = json.loads(calculate_position_size.invoke({
        "account_equity": 100000,
        "risk_per_trade_pct": 0.02,
        "entry_price": 150.0,
        "stop_loss_price": 145.0,
    }))
    assert result["shares"] == 400  # 2000 risk / 5 risk per share
    assert result["position_value"] == 60000.0


def test_calculate_stop_loss_atr():
    result = json.loads(calculate_stop_loss.invoke({
        "entry_price": 150.0,
        "atr": 3.0,
        "method": "atr",
        "multiplier": 2.0,
        "pct": 0.05,
    }))
    assert result["stop_loss"] == 144.0  # 150 - (3 * 2)
    assert result["take_profit"] == 162.0  # 150 + (3 * 2 * 2)
    assert result["risk_reward_ratio"] == 2.0


def test_get_portfolio_exposure_empty():
    result = json.loads(get_portfolio_exposure.invoke(json.dumps([])))
    assert result["num_positions"] == 0
    assert result["concentration_risk"] == "none"


def test_get_portfolio_exposure():
    positions = [
        {"symbol": "AAPL", "market_value": 50000, "unrealized_pnl": 1000},
        {"symbol": "MSFT", "market_value": 30000, "unrealized_pnl": -500},
    ]
    result = json.loads(get_portfolio_exposure.invoke(json.dumps(positions)))
    assert result["num_positions"] == 2
    assert result["total_exposure"] == 80000.0
