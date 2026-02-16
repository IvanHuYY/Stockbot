"""LangGraph trading pipeline - wires all agents into a StateGraph."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from langgraph.graph import END, START, StateGraph

from config.settings import Settings
from stockbot.agents.market_analyst import create_market_analyst_node
from stockbot.agents.portfolio_manager import create_portfolio_manager_node
from stockbot.agents.risk_manager import create_risk_manager_node
from stockbot.agents.state import AgentState
from stockbot.broker.client import AlpacaClient

logger = structlog.get_logger()


def build_trading_graph(broker: AlpacaClient, settings: Settings):
    """Build and compile the full trading agent pipeline."""
    graph = StateGraph(AgentState)

    # Create agent nodes
    market_analyst = create_market_analyst_node(settings)
    risk_manager = create_risk_manager_node(settings)
    portfolio_manager = create_portfolio_manager_node(settings, broker)

    # Add all nodes
    graph.add_node("data_loader", _create_data_loader(broker, settings))
    graph.add_node("market_analyst", market_analyst)
    graph.add_node("risk_manager", risk_manager)
    graph.add_node("portfolio_manager", portfolio_manager)
    graph.add_node("executor", _create_executor(broker))
    graph.add_node("reporter", _create_reporter())

    # Define edges: sequential pipeline
    graph.add_edge(START, "data_loader")
    graph.add_edge("data_loader", "market_analyst")
    graph.add_edge("market_analyst", "risk_manager")
    graph.add_edge("risk_manager", "portfolio_manager")

    # Conditional: execute trades or skip to reporter
    graph.add_conditional_edges(
        "portfolio_manager",
        _should_execute,
        {"executor": "executor", "reporter": "reporter"},
    )
    graph.add_edge("executor", "reporter")
    graph.add_edge("reporter", END)

    compiled = graph.compile()
    logger.info("Trading graph compiled successfully")
    return compiled


def _should_execute(state: AgentState) -> str:
    """Decide whether to execute trades or skip to reporting."""
    decisions = state.get("trade_decisions", [])
    has_trades = any(d["action"] != "hold" and d["quantity"] > 0 for d in decisions)
    return "executor" if has_trades else "reporter"


def _create_data_loader(broker: AlpacaClient, settings: Settings):
    """Create the data loader node that fetches all needed data."""
    from datetime import timedelta

    from stockbot.data.market_data import MarketDataService

    def data_loader_node(state: AgentState) -> dict:
        cycle_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc)
        logger.info("Starting data load", cycle_id=cycle_id)

        market_data_svc = MarketDataService(broker.data_client)
        symbols = state["symbols_to_analyze"]

        # Fetch market data
        market_data = {}
        start_date = now - timedelta(days=120)
        bars = market_data_svc.get_multi_bars(symbols, timeframe="1day", start=start_date, end=now)

        for symbol in symbols:
            df = bars.get(symbol)
            if df is not None and not df.empty:
                ohlcv = df.reset_index().to_dict(orient="records")
                # Convert timestamps to strings for JSON serialization
                for row in ohlcv:
                    for k, v in row.items():
                        if hasattr(v, "isoformat"):
                            row[k] = v.isoformat()
                market_data[symbol] = {"ohlcv": ohlcv}
            else:
                market_data[symbol] = {"ohlcv": []}

        # Fetch account info
        try:
            acct = broker.account.get_account_info()
            account_info = {
                "equity": acct.equity,
                "cash": acct.cash,
                "buying_power": acct.buying_power,
                "portfolio_value": acct.portfolio_value,
                "daily_pnl": acct.daily_pnl,
                "daily_pnl_pct": acct.daily_pnl_pct,
            }
        except Exception as e:
            logger.error("Failed to fetch account info", error=str(e))
            account_info = {}

        # Fetch current positions
        try:
            pos = broker.positions.get_all_positions()
            current_positions = [
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
                for p in pos
            ]
        except Exception as e:
            logger.error("Failed to fetch positions", error=str(e))
            current_positions = []

        # Fetch news
        news_data = []
        try:
            from stockbot.data.news import NewsService

            news_svc = NewsService(settings.alpaca_api_key, settings.alpaca_secret_key)
            for symbol in symbols:
                articles = news_svc.get_news_for_symbol(symbol, limit=5)
                for a in articles:
                    news_data.append({
                        "title": a.title,
                        "summary": a.summary,
                        "source": a.source,
                        "symbols": a.symbols,
                        "published_at": a.published_at.isoformat() if a.published_at else "",
                    })
        except Exception as e:
            logger.warning("Failed to fetch news", error=str(e))

        logger.info(
            "Data load complete",
            cycle_id=cycle_id,
            symbols=len(symbols),
            news_articles=len(news_data),
        )

        return {
            "market_data": market_data,
            "news_data": news_data,
            "account_info": account_info,
            "current_positions": current_positions,
            "cycle_id": cycle_id,
            "cycle_timestamp": now.isoformat(),
            "messages": [],
        }

    return data_loader_node


def _create_executor(broker: AlpacaClient):
    """Create the order executor node (deterministic, no LLM)."""

    def executor_node(state: AgentState) -> dict:
        results = []
        for decision in state.get("trade_decisions", []):
            if decision["action"] == "hold" or decision["quantity"] <= 0:
                continue

            symbol = decision["symbol"]
            logger.info(
                "Executing trade",
                symbol=symbol,
                action=decision["action"],
                qty=decision["quantity"],
                order_type=decision["order_type"],
            )

            try:
                if decision["order_type"] == "bracket" and decision["stop_loss"] and decision["take_profit"]:
                    order = broker.orders.submit_bracket_order(
                        symbol=symbol,
                        qty=decision["quantity"],
                        side=decision["action"],
                        take_profit=decision["take_profit"],
                        stop_loss=decision["stop_loss"],
                    )
                elif decision["order_type"] == "limit" and decision["limit_price"]:
                    order = broker.orders.submit_limit_order(
                        symbol=symbol,
                        qty=decision["quantity"],
                        side=decision["action"],
                        limit_price=decision["limit_price"],
                    )
                else:
                    order = broker.orders.submit_market_order(
                        symbol=symbol,
                        qty=decision["quantity"],
                        side=decision["action"],
                    )

                results.append({
                    "symbol": symbol,
                    "order_id": str(order.id),
                    "status": "submitted",
                    "error": "",
                })
                logger.info("Order submitted", symbol=symbol, order_id=str(order.id))

            except Exception as e:
                results.append({
                    "symbol": symbol,
                    "order_id": "",
                    "status": "failed",
                    "error": str(e),
                })
                logger.error("Order failed", symbol=symbol, error=str(e))

        return {"execution_results": results}

    return executor_node


def _create_reporter():
    """Create the reporter node that logs the full cycle to the database."""

    def reporter_node(state: AgentState) -> dict:
        from stockbot.db.session import get_session, init_db
        from stockbot.db.models import AgentDecision, Trade

        cycle_id = state.get("cycle_id", "unknown")
        logger.info("Reporting cycle results", cycle_id=cycle_id)

        try:
            init_db()
            session_gen = get_session()
            session = next(session_gen)

            # Log agent decisions
            for analysis in state.get("analyses", []):
                session.add(AgentDecision(
                    cycle_id=cycle_id,
                    agent_name="market_analyst",
                    symbol=analysis["symbol"],
                    input_data="",
                    output_data=json.dumps(dict(analysis)),
                    reasoning=analysis["reasoning"],
                ))

            for ra in state.get("risk_assessments", []):
                session.add(AgentDecision(
                    cycle_id=cycle_id,
                    agent_name="risk_manager",
                    symbol=ra["symbol"],
                    input_data="",
                    output_data=json.dumps(dict(ra)),
                    reasoning=ra["reasoning"],
                ))

            for td in state.get("trade_decisions", []):
                session.add(AgentDecision(
                    cycle_id=cycle_id,
                    agent_name="portfolio_manager",
                    symbol=td["symbol"],
                    input_data="",
                    output_data=json.dumps(dict(td)),
                    reasoning=td["reasoning"],
                ))

            # Log executed trades
            for er in state.get("execution_results", []):
                td = next(
                    (d for d in state.get("trade_decisions", []) if d["symbol"] == er["symbol"]),
                    None,
                )
                if td and td["action"] != "hold":
                    session.add(Trade(
                        symbol=er["symbol"],
                        side=td["action"],
                        quantity=td["quantity"],
                        order_type=td["order_type"],
                        order_id=er.get("order_id", ""),
                        status=er["status"],
                        stop_loss=td.get("stop_loss"),
                        take_profit=td.get("take_profit"),
                        cycle_id=cycle_id,
                        reasoning=td["reasoning"],
                    ))

            session.commit()
            logger.info("Cycle reported to database", cycle_id=cycle_id)

        except Exception as e:
            logger.error("Failed to report cycle", cycle_id=cycle_id, error=str(e))

        return {"messages": []}

    return reporter_node
