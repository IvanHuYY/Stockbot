"""Strategy comparison - compare multiple backtest results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import plotly.graph_objects as go

if TYPE_CHECKING:
    from stockbot.backtesting.engine import BacktestResult


@dataclass
class ComparisonReport:
    strategy_names: list[str]
    metrics_table: dict[str, dict]  # strategy -> metrics
    ranking: list[str]  # strategies ranked by Sharpe ratio


class StrategyComparator:
    """Compare multiple backtest results side-by-side."""

    def compare(self, results: dict[str, BacktestResult]) -> ComparisonReport:
        """Compare multiple strategy results."""
        metrics_table = {}
        for name, result in results.items():
            metrics_table[name] = result.metrics

        # Rank by Sharpe ratio
        ranking = sorted(
            results.keys(),
            key=lambda k: results[k].metrics.get("sharpe_ratio", 0),
            reverse=True,
        )

        return ComparisonReport(
            strategy_names=list(results.keys()),
            metrics_table=metrics_table,
            ranking=ranking,
        )

    def create_comparison_chart(self, results: dict[str, BacktestResult]) -> go.Figure:
        """Create overlaid equity curves for comparison."""
        fig = go.Figure()

        colors = ["#58a6ff", "#3fb950", "#f0883e", "#f85149", "#bc8cff"]

        for i, (name, result) in enumerate(results.items()):
            eq = result.equity_curve
            if not eq.empty:
                # Normalize to starting value of 1.0
                normalized = eq / eq.iloc[0]
                fig.add_trace(
                    go.Scatter(
                        x=normalized.index,
                        y=normalized.values,
                        mode="lines",
                        name=name,
                        line=dict(color=colors[i % len(colors)], width=2),
                    )
                )

        fig.update_layout(
            title="Strategy Comparison (Normalized)",
            template="plotly_dark",
            height=500,
            yaxis_title="Normalized Return",
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
        )

        return fig
