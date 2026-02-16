"""Backtest report generation - HTML reports with charts."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import plotly.graph_objects as go
from plotly.subplots import make_subplots

if TYPE_CHECKING:
    from stockbot.backtesting.engine import BacktestResult


class BacktestReport:
    """Generate HTML backtest reports with interactive charts."""

    def generate_html(self, result: BacktestResult, output_path: str) -> None:
        """Generate an HTML report with equity curve, drawdown, and metrics."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        fig = self._create_charts(result)
        metrics_html = self._create_metrics_table(result)
        trades_html = self._create_trades_table(result)

        chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Stockbot Backtest Report - {result.config.strategy_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               margin: 0; padding: 20px; background: #0d1117; color: #c9d1d9; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        h2 {{ color: #79c0ff; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 15px; margin: 20px 0; }}
        .metric-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                       padding: 15px; }}
        .metric-label {{ color: #8b949e; font-size: 0.85em; }}
        .metric-value {{ color: #f0f6fc; font-size: 1.4em; font-weight: bold; margin-top: 5px; }}
        .positive {{ color: #3fb950; }}
        .negative {{ color: #f85149; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #30363d; }}
        th {{ background: #161b22; color: #8b949e; }}
        .chart {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Backtest Report: {result.config.strategy_name}</h1>
        <p>Period: {result.config.start_date.strftime('%Y-%m-%d')} to {result.config.end_date.strftime('%Y-%m-%d')}
        | Symbols: {', '.join(result.config.symbols)}
        | Initial Capital: ${result.config.initial_capital:,.0f}</p>

        <h2>Performance Metrics</h2>
        {metrics_html}

        <h2>Equity Curve & Drawdown</h2>
        <div class="chart">{chart_html}</div>

        <h2>Trade Log ({result.metrics.get('num_trades', 0)} trades)</h2>
        {trades_html}
    </div>
</body>
</html>"""

        with open(output_path, "w") as f:
            f.write(html)

    def _create_charts(self, result: BacktestResult) -> go.Figure:
        """Create equity curve and drawdown charts."""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("Equity Curve", "Drawdown"),
            row_heights=[0.7, 0.3],
        )

        eq = result.equity_curve

        # Equity curve
        fig.add_trace(
            go.Scatter(
                x=eq.index, y=eq.values,
                mode="lines", name="Portfolio",
                line=dict(color="#58a6ff", width=2),
            ),
            row=1, col=1,
        )

        # Initial capital line
        fig.add_hline(
            y=result.config.initial_capital,
            line_dash="dash", line_color="#8b949e",
            annotation_text="Initial Capital",
            row=1, col=1,
        )

        # Drawdown
        returns = eq.pct_change().dropna()
        cumulative = (1 + returns).cumprod()
        drawdown = (cumulative - cumulative.cummax()) / cumulative.cummax()

        fig.add_trace(
            go.Scatter(
                x=drawdown.index, y=drawdown.values,
                mode="lines", name="Drawdown",
                fill="tozeroy",
                line=dict(color="#f85149", width=1),
                fillcolor="rgba(248, 81, 73, 0.2)",
            ),
            row=2, col=1,
        )

        fig.update_layout(
            template="plotly_dark",
            height=600,
            showlegend=False,
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
        )

        return fig

    def _create_metrics_table(self, result: BacktestResult) -> str:
        """Create metrics HTML grid."""
        m = result.metrics
        cards = [
            ("Total Return", f"{m.get('total_return', 0):.2%}", m.get("total_return", 0) >= 0),
            ("Annualized Return", f"{m.get('annualized_return', 0):.2%}", m.get("annualized_return", 0) >= 0),
            ("Sharpe Ratio", f"{m.get('sharpe_ratio', 0):.2f}", m.get("sharpe_ratio", 0) >= 1),
            ("Sortino Ratio", f"{m.get('sortino_ratio', 0):.2f}", m.get("sortino_ratio", 0) >= 1),
            ("Max Drawdown", f"{m.get('max_drawdown', 0):.2%}", False),
            ("Win Rate", f"{m.get('win_rate', 0):.1%}", m.get("win_rate", 0) >= 0.5),
            ("Profit Factor", f"{m.get('profit_factor', 0):.2f}", m.get("profit_factor", 0) >= 1),
            ("Calmar Ratio", f"{m.get('calmar_ratio', 0):.2f}", m.get("calmar_ratio", 0) >= 1),
            ("Total Trades", str(m.get("num_trades", 0)), True),
            ("Avg Win", f"${m.get('avg_win', 0):,.2f}", True),
            ("Avg Loss", f"${m.get('avg_loss', 0):,.2f}", False),
            ("Win/Loss Ratio", f"{m.get('avg_win_loss_ratio', 0):.2f}", m.get("avg_win_loss_ratio", 0) >= 1),
        ]

        html = '<div class="metrics-grid">'
        for label, value, is_positive in cards:
            css_class = "positive" if is_positive else "negative"
            html += f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value {css_class}">{value}</div>
            </div>"""
        html += "</div>"
        return html

    def _create_trades_table(self, result: BacktestResult) -> str:
        """Create trades HTML table."""
        trades = result.trades[-50:]  # Last 50 trades
        if not trades:
            return "<p>No trades executed.</p>"

        html = """<table>
        <tr><th>Date</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>P&L</th><th>Reason</th></tr>"""

        for t in trades:
            pnl = t.get("pnl", 0)
            pnl_class = "positive" if pnl > 0 else "negative" if pnl < 0 else ""
            date = t.get("timestamp", "")
            if hasattr(date, "strftime"):
                date = date.strftime("%Y-%m-%d")

            html += f"""
            <tr>
                <td>{date}</td>
                <td>{t.get('symbol', '')}</td>
                <td>{t.get('side', '')}</td>
                <td>{t.get('quantity', 0)}</td>
                <td>${t.get('price', 0):,.2f}</td>
                <td class="{pnl_class}">${pnl:,.2f}</td>
                <td>{t.get('reason', '')[:60]}</td>
            </tr>"""

        html += "</table>"
        return html
