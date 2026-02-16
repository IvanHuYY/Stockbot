"""Risk Manager agent - evaluates risk for proposed trades."""

from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from stockbot.agents.llm import get_llm, load_prompt
from stockbot.agents.state import AgentState, RiskAssessment
from stockbot.agents.tools.risk_tools import (
    calculate_position_size,
    calculate_stop_loss,
    calculate_var,
    get_portfolio_exposure,
)

logger = structlog.get_logger()


def create_risk_manager_node(settings: Any):
    """Create the Risk Manager node for the trading graph."""
    llm = get_llm(settings)
    tools = [calculate_position_size, calculate_var, calculate_stop_loss, get_portfolio_exposure]
    system_prompt = load_prompt("risk_manager.md")
    risk_agent = create_react_agent(llm, tools)

    max_position_pct = settings.max_position_pct
    max_portfolio_risk_pct = settings.max_portfolio_risk_pct
    max_daily_loss_pct = settings.max_daily_loss_pct

    def risk_manager_node(state: AgentState) -> dict:
        assessments: list[RiskAssessment] = []
        analyses = state.get("analyses", [])
        account = state.get("account_info", {})
        positions = state.get("current_positions", [])

        # Only assess symbols with actionable recommendations
        actionable = [a for a in analyses if a["recommendation"] not in ("hold",)]

        if not actionable:
            logger.info("No actionable recommendations, skipping risk assessment")
            return {"risk_assessments": []}

        for analysis in actionable:
            symbol = analysis["symbol"]
            logger.info("Assessing risk", symbol=symbol, agent="risk_manager")

            prompt = f"""Assess the risk for a potential trade on {symbol}.

Market Analyst recommendation: {analysis["recommendation"]} (confidence: {analysis["confidence"]})
Reasoning: {analysis["reasoning"]}
Technical signals: {json.dumps(analysis["technical_signals"])}
Support level: {analysis["support_level"]}
Resistance level: {analysis["resistance_level"]}

Account info:
- Equity: ${account.get("equity", 0):,.2f}
- Cash: ${account.get("cash", 0):,.2f}
- Buying power: ${account.get("buying_power", 0):,.2f}
- Daily P&L: ${account.get("daily_pnl", 0):,.2f} ({account.get("daily_pnl_pct", 0):.2%})

Current positions:
{json.dumps(positions, indent=2)}

Use the available tools to:
1. Calculate position size (use 2% risk per trade)
2. Calculate stop loss and take profit levels
3. Analyze portfolio exposure

Hard limits to enforce:
- Max position size: {max_position_pct:.0%} of equity
- Max portfolio risk: {max_portfolio_risk_pct:.0%}
- Min risk/reward: 2:1
- Max daily loss: {max_daily_loss_pct:.0%} (if exceeded, reject ALL trades)

Return your assessment as a JSON object with these exact fields:
- symbol: "{symbol}"
- approved: true or false
- max_position_size: dollar amount
- suggested_stop_loss: price level
- suggested_take_profit: price level
- risk_reward_ratio: calculated ratio
- portfolio_risk_after: projected risk percentage
- reasoning: explanation

Return ONLY the JSON object."""

            try:
                result = risk_agent.invoke({
                    "messages": [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=prompt),
                    ]
                })

                assessment = _parse_assessment(result, symbol)

                # HARD CONSTRAINT ENFORCEMENT (code overrides LLM)
                assessment = _enforce_risk_limits(
                    assessment, account, positions, settings
                )

                assessments.append(assessment)
                logger.info(
                    "Risk assessment complete",
                    symbol=symbol,
                    approved=assessment["approved"],
                    risk_reward=assessment["risk_reward_ratio"],
                )
            except Exception as e:
                logger.error("Risk assessment failed", symbol=symbol, error=str(e))
                assessments.append(_rejected_assessment(symbol, f"Assessment error: {e}"))

        return {"risk_assessments": assessments}

    return risk_manager_node


def _enforce_risk_limits(
    assessment: RiskAssessment,
    account: dict,
    positions: list,
    settings: Any,
) -> RiskAssessment:
    """Enforce hard risk limits regardless of what the LLM decided."""
    equity = account.get("equity", 0)
    daily_pnl_pct = account.get("daily_pnl_pct", 0)
    reasons = []

    # Check daily loss limit
    if daily_pnl_pct < -settings.max_daily_loss_pct:
        assessment["approved"] = False
        reasons.append(
            f"Daily loss ({daily_pnl_pct:.2%}) exceeds max ({-settings.max_daily_loss_pct:.0%})"
        )

    # Check position size limit
    if equity > 0:
        max_position_value = equity * settings.max_position_pct
        if assessment["max_position_size"] > max_position_value:
            assessment["max_position_size"] = max_position_value
            reasons.append(f"Position size capped to {settings.max_position_pct:.0%} of equity")

    # Check risk/reward ratio
    if assessment["risk_reward_ratio"] < 2.0:
        assessment["approved"] = False
        reasons.append(
            f"Risk/reward ratio ({assessment['risk_reward_ratio']:.1f}) below minimum (2.0)"
        )

    # Check total portfolio exposure
    total_exposure = sum(abs(p.get("market_value", 0)) for p in positions)
    if equity > 0:
        current_risk_pct = total_exposure / equity
        if current_risk_pct > settings.max_portfolio_risk_pct:
            assessment["approved"] = False
            reasons.append(
                f"Portfolio risk ({current_risk_pct:.0%}) exceeds max "
                f"({settings.max_portfolio_risk_pct:.0%})"
            )

    if reasons:
        assessment["reasoning"] += " | HARD LIMITS: " + "; ".join(reasons)

    return assessment


def _parse_assessment(result: dict, symbol: str) -> RiskAssessment:
    """Parse the agent's response into a RiskAssessment."""
    messages = result.get("messages", [])
    if not messages:
        return _rejected_assessment(symbol, "No response from risk agent")

    last_message = messages[-1]
    content = last_message.content if hasattr(last_message, "content") else str(last_message)

    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        return RiskAssessment(
            symbol=data.get("symbol", symbol),
            approved=bool(data.get("approved", False)),
            max_position_size=float(data.get("max_position_size", 0)),
            suggested_stop_loss=float(data.get("suggested_stop_loss", 0)),
            suggested_take_profit=float(data.get("suggested_take_profit", 0)),
            risk_reward_ratio=float(data.get("risk_reward_ratio", 0)),
            portfolio_risk_after=float(data.get("portfolio_risk_after", 0)),
            reasoning=data.get("reasoning", ""),
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse risk assessment", symbol=symbol, error=str(e))
        return _rejected_assessment(symbol, f"Parse error: {e}")


def _rejected_assessment(symbol: str, reason: str) -> RiskAssessment:
    """Return a default rejected assessment."""
    return RiskAssessment(
        symbol=symbol,
        approved=False,
        max_position_size=0,
        suggested_stop_loss=0,
        suggested_take_profit=0,
        risk_reward_ratio=0,
        portfolio_risk_after=0,
        reasoning=reason,
    )
