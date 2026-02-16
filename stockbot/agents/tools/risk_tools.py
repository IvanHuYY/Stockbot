"""Risk management tools for the Risk Manager agent."""

from __future__ import annotations

import json
import math

import numpy as np
from langchain_core.tools import tool


@tool
def calculate_position_size(
    account_equity: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_loss_price: float,
) -> str:
    """Calculate position size based on risk-per-trade model.
    Args:
        account_equity: Total account equity in dollars
        risk_per_trade_pct: Max risk per trade as decimal (e.g. 0.02 for 2%)
        entry_price: Expected entry price
        stop_loss_price: Stop loss price level
    Returns: JSON with position size details."""
    risk_amount = account_equity * risk_per_trade_pct
    price_risk = abs(entry_price - stop_loss_price)

    if price_risk == 0:
        return json.dumps({"error": "Entry price equals stop loss price"})

    shares = math.floor(risk_amount / price_risk)
    position_value = shares * entry_price
    position_pct = position_value / account_equity if account_equity > 0 else 0

    return json.dumps({
        "shares": shares,
        "position_value": round(position_value, 2),
        "position_pct": round(position_pct, 4),
        "risk_amount": round(risk_amount, 2),
        "risk_per_share": round(price_risk, 2),
    })


@tool
def calculate_var(returns_json: str, confidence: float = 0.95) -> str:
    """Calculate Value at Risk for a series of returns.
    Args:
        returns_json: JSON array of daily return values (decimals)
        confidence: Confidence level (default 0.95)
    Returns: JSON with VaR metrics."""
    returns = np.array(json.loads(returns_json))

    if len(returns) < 10:
        return json.dumps({"error": "Need at least 10 data points"})

    # Historical VaR
    sorted_returns = np.sort(returns)
    index = int((1 - confidence) * len(sorted_returns))
    historical_var = float(sorted_returns[index])

    # Parametric VaR (assuming normal distribution)
    mean = float(np.mean(returns))
    std = float(np.std(returns))
    from scipy.stats import norm

    z_score = norm.ppf(1 - confidence)
    parametric_var = mean + z_score * std

    # Expected Shortfall (CVaR)
    tail_returns = sorted_returns[:index + 1]
    cvar = float(np.mean(tail_returns)) if len(tail_returns) > 0 else historical_var

    return json.dumps({
        "historical_var": round(historical_var, 6),
        "parametric_var": round(parametric_var, 6),
        "expected_shortfall": round(cvar, 6),
        "confidence": confidence,
        "daily_volatility": round(std, 6),
        "annualized_volatility": round(std * math.sqrt(252), 6),
    })


@tool
def calculate_stop_loss(
    entry_price: float,
    atr: float,
    method: str = "atr",
    multiplier: float = 2.0,
    pct: float = 0.05,
) -> str:
    """Calculate stop loss and take profit levels.
    Args:
        entry_price: Entry price for the position
        atr: Average True Range (14-period)
        method: 'atr' for ATR-based or 'percentage' for fixed percentage
        multiplier: ATR multiplier for stop distance (default 2.0)
        pct: Percentage for stop loss (used when method='percentage')
    Returns: JSON with stop loss and take profit levels."""
    if method == "atr":
        stop_distance = atr * multiplier
        take_profit_distance = atr * multiplier * 2  # 2:1 reward/risk
    else:
        stop_distance = entry_price * pct
        take_profit_distance = stop_distance * 2

    stop_loss = entry_price - stop_distance
    take_profit = entry_price + take_profit_distance
    risk_reward = take_profit_distance / stop_distance if stop_distance > 0 else 0

    return json.dumps({
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "stop_distance": round(stop_distance, 2),
        "stop_distance_pct": round(stop_distance / entry_price * 100, 2),
        "risk_reward_ratio": round(risk_reward, 2),
    })


@tool
def get_portfolio_exposure(positions_json: str) -> str:
    """Analyze current portfolio exposure by position.
    Args:
        positions_json: JSON array of position objects with
            'symbol', 'market_value', 'unrealized_pnl' fields
    Returns: JSON with exposure analysis."""
    positions = json.loads(positions_json)

    if not positions:
        return json.dumps({
            "total_exposure": 0,
            "num_positions": 0,
            "positions": [],
            "concentration_risk": "none",
        })

    total_value = sum(abs(p.get("market_value", 0)) for p in positions)

    exposure = []
    for p in positions:
        mv = abs(p.get("market_value", 0))
        exposure.append({
            "symbol": p["symbol"],
            "market_value": round(mv, 2),
            "weight": round(mv / total_value, 4) if total_value > 0 else 0,
            "unrealized_pnl": round(p.get("unrealized_pnl", 0), 2),
        })

    exposure.sort(key=lambda x: x["weight"], reverse=True)
    max_weight = exposure[0]["weight"] if exposure else 0

    if max_weight > 0.3:
        concentration = "high"
    elif max_weight > 0.15:
        concentration = "moderate"
    else:
        concentration = "low"

    return json.dumps({
        "total_exposure": round(total_value, 2),
        "num_positions": len(positions),
        "positions": exposure,
        "max_position_weight": round(max_weight, 4),
        "concentration_risk": concentration,
    })
