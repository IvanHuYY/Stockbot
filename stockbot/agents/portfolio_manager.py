"""Portfolio Manager agent - makes final trade decisions."""

from __future__ import annotations

import json
import math
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from stockbot.agents.llm import get_llm, load_prompt
from stockbot.agents.state import AgentState, TradeDecision
from stockbot.agents.tools.broker_tools import create_broker_tools

logger = structlog.get_logger()


def create_portfolio_manager_node(settings: Any, broker: Any):
    """Create the Portfolio Manager node for the trading graph."""
    llm = get_llm(settings)
    tools = create_broker_tools(broker)
    system_prompt = load_prompt("portfolio_manager.md")
    pm_agent = create_react_agent(llm, tools)

    def portfolio_manager_node(state: AgentState) -> dict:
        decisions: list[TradeDecision] = []
        analyses = state.get("analyses", [])
        risk_assessments = state.get("risk_assessments", [])
        account = state.get("account_info", {})
        positions = state.get("current_positions", [])

        # Only consider risk-approved trades
        approved = {ra["symbol"]: ra for ra in risk_assessments if ra["approved"]}

        if not approved:
            logger.info("No approved trades, all holds")
            for a in analyses:
                decisions.append(_hold_decision(a["symbol"], "No risk-approved trades"))
            return {"trade_decisions": decisions}

        # Build context for the Portfolio Manager
        analyses_by_symbol = {a["symbol"]: a for a in analyses}

        prompt = f"""Make final trade decisions based on the following:

## Approved Trades (Risk Manager approved)
{json.dumps(list(approved.values()), indent=2)}

## Market Analyst Recommendations
{json.dumps([a for a in analyses if a["symbol"] in approved], indent=2)}

## Account Info
- Equity: ${account.get("equity", 0):,.2f}
- Cash: ${account.get("cash", 0):,.2f}
- Buying power: ${account.get("buying_power", 0):,.2f}

## Current Positions
{json.dumps(positions, indent=2)}

For each approved symbol, decide whether to execute.
Use the available tools to check positions and buying power.

Return a JSON array of trade decisions, each with:
- action: "buy", "sell", or "hold"
- symbol: ticker
- quantity: number of shares (integer)
- order_type: "market", "limit", or "bracket"
- limit_price: null for market orders
- stop_loss: from risk assessment
- take_profit: from risk assessment
- reasoning: your explanation

Rules:
- Maintain at least 20% cash reserve
- Max 10 positions total
- Prefer bracket orders for automatic risk management
- If already holding the symbol, consider the existing position

Return ONLY the JSON array."""

        try:
            result = pm_agent.invoke({
                "messages": [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=prompt),
                ]
            })

            parsed = _parse_decisions(result)
            if parsed:
                # Validate each decision
                for d in parsed:
                    symbol = d["symbol"]
                    if symbol in approved:
                        ra = approved[symbol]
                        # Ensure stop/take-profit from risk manager
                        if d["stop_loss"] is None or d["stop_loss"] == 0:
                            d["stop_loss"] = ra["suggested_stop_loss"]
                        if d["take_profit"] is None or d["take_profit"] == 0:
                            d["take_profit"] = ra["suggested_take_profit"]

                        # Enforce position size limit
                        equity = account.get("equity", 0)
                        if equity > 0 and d["quantity"] > 0:
                            price = analyses_by_symbol.get(symbol, {}).get(
                                "technical_signals", {}
                            ).get("current_price", 0)
                            if price > 0:
                                max_shares = math.floor(
                                    ra["max_position_size"] / price
                                )
                                d["quantity"] = min(d["quantity"], max_shares)

                    decisions.append(d)
                    logger.info(
                        "Trade decision",
                        symbol=d["symbol"],
                        action=d["action"],
                        quantity=d["quantity"],
                    )
            else:
                for symbol in approved:
                    decisions.append(_hold_decision(symbol, "Failed to parse PM decisions"))

        except Exception as e:
            logger.error("Portfolio manager failed", error=str(e))
            for symbol in approved:
                decisions.append(_hold_decision(symbol, f"PM error: {e}"))

        # Add hold decisions for non-approved symbols
        for a in analyses:
            if a["symbol"] not in approved and a["symbol"] not in {d["symbol"] for d in decisions}:
                decisions.append(_hold_decision(a["symbol"], "Not approved by Risk Manager"))

        return {"trade_decisions": decisions}

    return portfolio_manager_node


def _parse_decisions(result: dict) -> list[TradeDecision]:
    """Parse the agent's response into TradeDecisions."""
    messages = result.get("messages", [])
    if not messages:
        return []

    last_message = messages[-1]
    content = last_message.content if hasattr(last_message, "content") else str(last_message)

    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        if isinstance(data, dict):
            data = [data]

        decisions = []
        for d in data:
            decisions.append(TradeDecision(
                action=d.get("action", "hold"),
                symbol=d.get("symbol", ""),
                quantity=int(d.get("quantity", 0)),
                order_type=d.get("order_type", "bracket"),
                limit_price=d.get("limit_price"),
                stop_loss=d.get("stop_loss"),
                take_profit=d.get("take_profit"),
                reasoning=d.get("reasoning", ""),
            ))
        return decisions
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse PM decisions", error=str(e))
        return []


def _hold_decision(symbol: str, reason: str) -> TradeDecision:
    return TradeDecision(
        action="hold",
        symbol=symbol,
        quantity=0,
        order_type="market",
        limit_price=None,
        stop_loss=None,
        take_profit=None,
        reasoning=reason,
    )
