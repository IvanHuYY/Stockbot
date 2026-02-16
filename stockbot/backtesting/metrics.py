"""Performance metrics for backtesting evaluation."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


class PerformanceMetrics:
    """Compute comprehensive performance metrics from equity curve and trades."""

    @staticmethod
    def compute(
        equity_curve: pd.Series,
        trades: list[dict],
        benchmark: pd.Series | None = None,
        risk_free_rate: float = 0.05,
    ) -> dict:
        """Compute all performance metrics.

        Args:
            equity_curve: Series of portfolio values indexed by date
            trades: List of trade dicts with 'pnl', 'side' fields
            benchmark: Optional benchmark equity curve for alpha/beta
            risk_free_rate: Annual risk-free rate

        Returns:
            Dict of metric name -> value
        """
        if equity_curve.empty or len(equity_curve) < 2:
            return _empty_metrics()

        returns = equity_curve.pct_change().dropna()
        daily_rf = risk_free_rate / 252

        # Basic returns
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        trading_days = len(returns)
        years = trading_days / 252
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # Risk metrics
        daily_vol = float(returns.std())
        annualized_vol = daily_vol * math.sqrt(252)

        # Sharpe ratio
        excess_returns = returns - daily_rf
        sharpe = float(excess_returns.mean() / returns.std()) * math.sqrt(252) if returns.std() > 0 else 0

        # Sortino ratio (only downside deviation)
        downside = returns[returns < daily_rf]
        downside_std = float(downside.std()) if len(downside) > 1 else daily_vol
        sortino = float(excess_returns.mean() / downside_std) * math.sqrt(252) if downside_std > 0 else 0

        # Drawdown
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = float(drawdown.min())

        # Max drawdown duration
        dd_duration = _max_drawdown_duration(drawdown)

        # Calmar ratio
        calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # Trade statistics
        trade_pnls = [t.get("pnl", 0) for t in trades if t.get("side") == "sell"]
        winning_trades = [p for p in trade_pnls if p > 0]
        losing_trades = [p for p in trade_pnls if p <= 0]

        num_trades = len(trade_pnls)
        win_rate = len(winning_trades) / num_trades if num_trades > 0 else 0

        avg_win = float(np.mean(winning_trades)) if winning_trades else 0
        avg_loss = float(np.mean(losing_trades)) if losing_trades else 0
        avg_win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

        gross_profit = sum(winning_trades)
        gross_loss = abs(sum(losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Exposure time (days with positions / total days)
        # Approximate from trades
        exposure_time = min(1.0, num_trades * 5 / trading_days) if trading_days > 0 else 0

        # Alpha & Beta (if benchmark provided)
        alpha = 0.0
        beta = 0.0
        information_ratio = 0.0

        if benchmark is not None and not benchmark.empty:
            bench_returns = benchmark.pct_change().dropna()
            # Align dates
            common = returns.index.intersection(bench_returns.index)
            if len(common) > 10:
                r = returns.loc[common]
                b = bench_returns.loc[common]
                cov = float(np.cov(r, b)[0][1])
                bench_var = float(b.var())
                beta = cov / bench_var if bench_var > 0 else 0
                alpha = float(r.mean() - beta * b.mean()) * 252

                tracking_error = float((r - b).std()) * math.sqrt(252)
                information_ratio = (
                    (float(r.mean() - b.mean()) * 252) / tracking_error
                    if tracking_error > 0
                    else 0
                )

        return {
            "total_return": round(total_return, 6),
            "annualized_return": round(annualized_return, 6),
            "annualized_volatility": round(annualized_vol, 6),
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "max_drawdown": round(max_drawdown, 6),
            "max_drawdown_duration_days": dd_duration,
            "calmar_ratio": round(calmar, 4),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(min(profit_factor, 999), 4),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_win_loss_ratio": round(min(avg_win_loss_ratio, 999), 4),
            "num_trades": num_trades,
            "exposure_time": round(exposure_time, 4),
            "alpha": round(alpha, 6),
            "beta": round(beta, 4),
            "information_ratio": round(information_ratio, 4),
        }


def _max_drawdown_duration(drawdown: pd.Series) -> int:
    """Calculate the maximum drawdown duration in trading days."""
    in_drawdown = drawdown < 0
    if not in_drawdown.any():
        return 0

    groups = (~in_drawdown).cumsum()
    dd_groups = groups[in_drawdown]
    if dd_groups.empty:
        return 0

    durations = dd_groups.groupby(dd_groups).count()
    return int(durations.max()) if not durations.empty else 0


def _empty_metrics() -> dict:
    return {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "annualized_volatility": 0.0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "max_drawdown": 0.0,
        "max_drawdown_duration_days": 0,
        "calmar_ratio": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "avg_win_loss_ratio": 0.0,
        "num_trades": 0,
        "exposure_time": 0.0,
        "alpha": 0.0,
        "beta": 0.0,
        "information_ratio": 0.0,
    }
