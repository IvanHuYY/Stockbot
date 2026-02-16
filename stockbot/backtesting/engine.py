"""Backtest engine - replays historical data through strategies."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import structlog

from stockbot.backtesting.metrics import PerformanceMetrics
from stockbot.backtesting.simulator import (
    OrderSimulator,
    SimulatedFill,
    SimulatedOrder,
    SimulatedPortfolio,
    SimulatedPosition,
)
from stockbot.data.features import FeatureEngineer
from stockbot.strategies.base import BaseStrategy
from stockbot.strategies.mean_reversion import MeanReversionStrategy
from stockbot.strategies.momentum import MomentumStrategy
from stockbot.strategies.composite import CompositeStrategy

logger = structlog.get_logger()

STRATEGY_MAP = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "composite": CompositeStrategy,
}


@dataclass
class BacktestConfig:
    symbols: list[str]
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100_000
    strategy_name: str = "momentum"
    commission: float = 0.0
    slippage_bps: float = 5.0
    risk_per_trade: float = 0.02
    max_position_pct: float = 0.10


@dataclass
class BacktestResult:
    config: BacktestConfig
    equity_curve: pd.Series = field(default_factory=pd.Series)
    trades: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    signals_log: list[dict] = field(default_factory=list)


class BacktestEngine:
    """Run backtests against historical data using rule-based strategies."""

    def __init__(self, config: BacktestConfig) -> None:
        self._config = config
        self._simulator = OrderSimulator(
            commission_per_trade=config.commission,
            slippage_bps=config.slippage_bps,
        )
        self._feature_eng = FeatureEngineer()

        # Create strategy
        strategy_cls = STRATEGY_MAP.get(config.strategy_name)
        if strategy_cls is None:
            raise ValueError(
                f"Unknown strategy: {config.strategy_name}. "
                f"Available: {list(STRATEGY_MAP)}"
            )
        self._strategy: BaseStrategy = strategy_cls()

    def run(self) -> BacktestResult:
        """Run the backtest and return results."""
        logger.info(
            "Starting backtest",
            strategy=self._config.strategy_name,
            symbols=self._config.symbols,
            start=self._config.start_date.isoformat(),
            end=self._config.end_date.isoformat(),
        )

        # Load and prepare data
        data = self._load_data()
        if not data:
            logger.error("No data loaded for backtest")
            return BacktestResult(config=self._config)

        # Get all dates across all symbols
        all_dates = sorted(set().union(*[set(df.index) for df in data.values()]))

        portfolio = SimulatedPortfolio(
            cash=self._config.initial_capital,
            initial_capital=self._config.initial_capital,
        )
        equity_points = []
        all_trades = []
        signals_log = []

        # Iterate through each trading day
        for i, date in enumerate(all_dates):
            # 1. Check stop-loss / take-profit for existing positions
            for symbol in list(portfolio.positions.keys()):
                pos = portfolio.positions[symbol]
                if symbol not in data or date not in data[symbol].index:
                    continue

                bar = data[symbol].loc[date]
                bar_low = float(bar["low"])
                bar_high = float(bar["high"])

                # Check stop-loss
                fill = self._simulator.check_stop_loss(pos, bar_low, bar_high, date)
                if fill is None:
                    fill = self._simulator.check_take_profit(pos, bar_high, date)

                if fill is not None:
                    pnl = (fill.fill_price - pos.avg_entry_price) * fill.quantity - fill.commission
                    portfolio.cash += fill.fill_price * fill.quantity - fill.commission
                    all_trades.append({
                        "symbol": symbol,
                        "side": "sell",
                        "quantity": fill.quantity,
                        "price": fill.fill_price,
                        "pnl": round(pnl, 2),
                        "reason": "stop_loss/take_profit",
                        "timestamp": date,
                    })
                    del portfolio.positions[symbol]

            # 2. Generate signals (use data up to current date)
            lookback_data = {}
            for symbol in self._config.symbols:
                if symbol in data:
                    mask = data[symbol].index <= date
                    lookback_data[symbol] = data[symbol][mask].tail(200)

            if i % 5 == 0 and lookback_data:  # Generate signals every 5 days
                signals = self._strategy.generate_signals(lookback_data)

                for signal in signals:
                    signals_log.append({
                        "date": date,
                        "symbol": signal.symbol,
                        "action": signal.action,
                        "strength": signal.strength,
                        "reason": signal.reason,
                    })

                    symbol = signal.symbol
                    if symbol not in data or date not in data[symbol].index:
                        continue

                    bar = data[symbol].loc[date]
                    bar_open = float(bar["open"])
                    bar_close = float(bar["close"])
                    atr = float(bar.get("atr_14", bar_close * 0.02)) if pd.notna(bar.get("atr_14")) else bar_close * 0.02

                    if signal.action == "buy" and symbol not in portfolio.positions:
                        # Calculate position size
                        max_value = portfolio.cash * self._config.max_position_pct
                        risk_amount = portfolio.cash * self._config.risk_per_trade
                        stop_distance = atr * 2
                        shares = min(
                            math.floor(risk_amount / stop_distance) if stop_distance > 0 else 0,
                            math.floor(max_value / bar_open) if bar_open > 0 else 0,
                        )

                        if shares > 0 and shares * bar_open < portfolio.cash * 0.8:
                            order = SimulatedOrder(
                                symbol=symbol, side="buy", quantity=shares, order_type="market"
                            )
                            fill = self._simulator.fill_market_order(order, bar_open, date)
                            cost = fill.fill_price * fill.quantity + fill.commission

                            portfolio.cash -= cost
                            portfolio.positions[symbol] = SimulatedPosition(
                                symbol=symbol,
                                quantity=fill.quantity,
                                avg_entry_price=fill.fill_price,
                                stop_loss=round(fill.fill_price - stop_distance, 2),
                                take_profit=round(fill.fill_price + stop_distance * 2, 2),
                                entry_time=date,
                            )
                            all_trades.append({
                                "symbol": symbol,
                                "side": "buy",
                                "quantity": fill.quantity,
                                "price": fill.fill_price,
                                "pnl": 0,
                                "reason": signal.reason,
                                "timestamp": date,
                            })

                    elif signal.action == "sell" and symbol in portfolio.positions:
                        pos = portfolio.positions[symbol]
                        order = SimulatedOrder(
                            symbol=symbol, side="sell", quantity=pos.quantity, order_type="market"
                        )
                        fill = self._simulator.fill_market_order(order, bar_open, date)
                        pnl = (fill.fill_price - pos.avg_entry_price) * fill.quantity - fill.commission
                        portfolio.cash += fill.fill_price * fill.quantity - fill.commission

                        all_trades.append({
                            "symbol": symbol,
                            "side": "sell",
                            "quantity": fill.quantity,
                            "price": fill.fill_price,
                            "pnl": round(pnl, 2),
                            "reason": signal.reason,
                            "timestamp": date,
                        })
                        del portfolio.positions[symbol]

            # 3. Record equity
            position_value = 0
            for symbol, pos in portfolio.positions.items():
                if symbol in data and date in data[symbol].index:
                    position_value += float(data[symbol].loc[date]["close"]) * pos.quantity

            total_equity = portfolio.cash + position_value
            equity_points.append((date, total_equity))

        # Build equity curve
        equity_curve = pd.Series(
            [e[1] for e in equity_points],
            index=[e[0] for e in equity_points],
            name="equity",
        )

        # Compute metrics
        metrics = PerformanceMetrics.compute(equity_curve, all_trades)

        result = BacktestResult(
            config=self._config,
            equity_curve=equity_curve,
            trades=all_trades,
            metrics=metrics,
            signals_log=signals_log,
        )

        logger.info(
            "Backtest complete",
            total_return=f"{metrics['total_return']:.2%}",
            sharpe=metrics["sharpe_ratio"],
            max_dd=f"{metrics['max_drawdown']:.2%}",
            num_trades=metrics["num_trades"],
        )

        return result

    def _load_data(self) -> dict[str, pd.DataFrame]:
        """Load historical data for all symbols."""
        from config.settings import Settings
        from stockbot.broker.client import AlpacaClient
        from stockbot.data.market_data import MarketDataService

        try:
            settings = Settings()
            broker = AlpacaClient(settings)
            data_svc = MarketDataService(broker.data_client)

            data = {}
            for symbol in self._config.symbols:
                df = data_svc.get_bars(
                    symbol,
                    timeframe="1day",
                    start=self._config.start_date,
                    end=self._config.end_date,
                )
                if not df.empty:
                    df = self._feature_eng.compute_all(df)
                    data[symbol] = df

            return data
        except Exception as e:
            logger.error("Failed to load backtest data", error=str(e))
            return {}
