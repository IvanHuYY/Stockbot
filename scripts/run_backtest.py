#!/usr/bin/env python3
"""CLI entry point for running backtests."""

from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Stockbot backtesting CLI")
console = Console()


@app.command()
def run(
    strategy: str = typer.Option("momentum", help="Strategy: momentum, mean_reversion, composite"),
    symbols: str = typer.Option("AAPL,MSFT,GOOGL", help="Comma-separated symbols"),
    start: str = typer.Option("2024-01-01", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option("2024-12-31", help="End date (YYYY-MM-DD)"),
    capital: float = typer.Option(100000, help="Initial capital"),
    output: str = typer.Option("reports/backtest.html", help="Output report path"),
):
    """Run a backtest with the specified strategy."""
    from stockbot.backtesting.engine import BacktestConfig, BacktestEngine

    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")

    console.print(f"\n📊 Running backtest: [bold]{strategy}[/bold]")
    console.print(f"   Symbols: {', '.join(symbol_list)}")
    console.print(f"   Period: {start} to {end}")
    console.print(f"   Capital: ${capital:,.0f}\n")

    config = BacktestConfig(
        symbols=symbol_list,
        start_date=start_date,
        end_date=end_date,
        initial_capital=capital,
        strategy_name=strategy,
    )

    engine = BacktestEngine(config)
    result = engine.run()

    # Display results
    table = Table(title="Backtest Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    metrics = result.metrics
    table.add_row("Total Return", f"{metrics['total_return']:.2%}")
    table.add_row("Annualized Return", f"{metrics['annualized_return']:.2%}")
    table.add_row("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    table.add_row("Sortino Ratio", f"{metrics['sortino_ratio']:.2f}")
    table.add_row("Max Drawdown", f"{metrics['max_drawdown']:.2%}")
    table.add_row("Win Rate", f"{metrics['win_rate']:.2%}")
    table.add_row("Profit Factor", f"{metrics['profit_factor']:.2f}")
    table.add_row("Total Trades", str(metrics["num_trades"]))

    console.print(table)

    # Generate report
    from stockbot.backtesting.report import BacktestReport

    report = BacktestReport()
    report.generate_html(result, output)
    console.print(f"\n📄 Report saved to: {output}")


@app.command()
def compare(
    strategies: str = typer.Option(
        "momentum,mean_reversion", help="Comma-separated strategies to compare"
    ),
    symbols: str = typer.Option("AAPL,MSFT,GOOGL", help="Comma-separated symbols"),
    start: str = typer.Option("2024-01-01", help="Start date"),
    end: str = typer.Option("2024-12-31", help="End date"),
    capital: float = typer.Option(100000, help="Initial capital"),
):
    """Compare multiple strategies side-by-side."""
    from stockbot.backtesting.comparison import StrategyComparator
    from stockbot.backtesting.engine import BacktestConfig, BacktestEngine

    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    strategy_list = [s.strip() for s in strategies.split(",")]
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")

    results = {}
    for strat in strategy_list:
        console.print(f"Running [bold]{strat}[/bold]...")
        config = BacktestConfig(
            symbols=symbol_list,
            start_date=start_date,
            end_date=end_date,
            initial_capital=capital,
            strategy_name=strat,
        )
        engine = BacktestEngine(config)
        results[strat] = engine.run()

    comparator = StrategyComparator()
    comparison = comparator.compare(results)

    # Display comparison table
    table = Table(title="Strategy Comparison")
    table.add_column("Metric", style="cyan")
    for strat in strategy_list:
        table.add_column(strat, style="green")

    for metric_name in ["total_return", "sharpe_ratio", "max_drawdown", "win_rate", "num_trades"]:
        row = [metric_name]
        for strat in strategy_list:
            val = results[strat].metrics.get(metric_name, 0)
            if isinstance(val, float) and metric_name != "sharpe_ratio":
                row.append(f"{val:.2%}")
            elif isinstance(val, float):
                row.append(f"{val:.2f}")
            else:
                row.append(str(val))
        table.add_row(*row)

    console.print(table)


if __name__ == "__main__":
    app()
