"""Market Analyst agent - analyzes technicals and sentiment per symbol."""

from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from stockbot.agents.llm import get_llm, load_prompt
from stockbot.agents.state import AgentState, MarketAnalysis
from stockbot.agents.tools.sentiment import analyze_news_sentiment
from stockbot.agents.tools.technical_analysis import (
    get_support_resistance,
    get_technical_indicators,
)

logger = structlog.get_logger()


def create_market_analyst_node(settings: Any):
    """Create the Market Analyst node for the trading graph."""
    llm = get_llm(settings)
    tools = [get_technical_indicators, get_support_resistance, analyze_news_sentiment]
    system_prompt = load_prompt("market_analyst.md")
    analyst_agent = create_react_agent(llm, tools)

    def market_analyst_node(state: AgentState) -> dict:
        analyses: list[MarketAnalysis] = []

        for symbol in state["symbols_to_analyze"]:
            logger.info("Analyzing symbol", symbol=symbol, agent="market_analyst")

            # Prepare data for the agent
            market_data = state.get("market_data", {}).get(symbol, {})
            news_data = [
                n for n in state.get("news_data", [])
                if symbol in n.get("symbols", [])
            ]

            prompt = f"""Analyze the stock {symbol} using the available tools.

Market data (OHLCV) is available as JSON:
{json.dumps(market_data.get("ohlcv", [])[-60:] if isinstance(market_data.get("ohlcv"), list) else [])}

Recent news articles:
{json.dumps([{"title": n.get("title", ""), "summary": n.get("summary", "")} for n in news_data[:10]])}

Use get_technical_indicators and get_support_resistance with the OHLCV data.
Use analyze_news_sentiment with the news articles.

Then provide your analysis as a JSON object with these exact fields:
- symbol: "{symbol}"
- technical_signals: dict of key indicator values
- sentiment_score: float from -1.0 to 1.0
- support_level: nearest support price
- resistance_level: nearest resistance price
- recommendation: one of "strong_buy", "buy", "hold", "sell", "strong_sell"
- confidence: float from 0.0 to 1.0
- reasoning: 2-3 sentence explanation

Return ONLY the JSON object, no other text."""

            try:
                result = analyst_agent.invoke({
                    "messages": [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=prompt),
                    ]
                })

                analysis = _parse_analysis(result, symbol)
                analyses.append(analysis)
                logger.info(
                    "Analysis complete",
                    symbol=symbol,
                    recommendation=analysis["recommendation"],
                    confidence=analysis["confidence"],
                )
            except Exception as e:
                logger.error("Analysis failed", symbol=symbol, error=str(e))
                analyses.append(_default_analysis(symbol))

        return {"analyses": analyses}

    return market_analyst_node


def _parse_analysis(result: dict, symbol: str) -> MarketAnalysis:
    """Parse the agent's response into a MarketAnalysis."""
    messages = result.get("messages", [])
    if not messages:
        return _default_analysis(symbol)

    last_message = messages[-1]
    content = last_message.content if hasattr(last_message, "content") else str(last_message)

    try:
        # Try to extract JSON from the response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        return MarketAnalysis(
            symbol=data.get("symbol", symbol),
            technical_signals=data.get("technical_signals", {}),
            sentiment_score=float(data.get("sentiment_score", 0.0)),
            support_level=float(data.get("support_level", 0.0)),
            resistance_level=float(data.get("resistance_level", 0.0)),
            recommendation=data.get("recommendation", "hold"),
            confidence=float(data.get("confidence", 0.3)),
            reasoning=data.get("reasoning", "Unable to parse full analysis"),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to parse analysis", symbol=symbol, error=str(e))
        return _default_analysis(symbol)


def _default_analysis(symbol: str) -> MarketAnalysis:
    """Return a default hold analysis when parsing fails."""
    return MarketAnalysis(
        symbol=symbol,
        technical_signals={},
        sentiment_score=0.0,
        support_level=0.0,
        resistance_level=0.0,
        recommendation="hold",
        confidence=0.1,
        reasoning="Insufficient data or analysis failure. Defaulting to hold.",
    )
