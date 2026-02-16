#!/usr/bin/env python3
"""CLI entry point for running the trading bot."""

import asyncio

import typer
from rich.console import Console

app = typer.Typer(help="Stockbot - AI-powered stock trading bot")
console = Console()


@app.command()
def run(
    paper: bool = typer.Option(True, help="Use paper trading mode"),
    cycle_minutes: int = typer.Option(15, help="Minutes between trading cycles"),
    single: bool = typer.Option(False, help="Run a single cycle then exit"),
):
    """Start the trading bot."""
    from config.settings import Settings
    from stockbot.engine.runner import TradingRunner

    settings = Settings(
        paper_trading=paper,
        trading_cycle_minutes=cycle_minutes,
    )

    mode = "[green]PAPER[/green]" if paper else "[red bold]LIVE[/red bold]"
    console.print(f"\n🤖 Stockbot starting in {mode} mode")
    console.print(f"   Cycle interval: {cycle_minutes} minutes\n")

    runner = TradingRunner(settings)

    if single:
        console.print("Running single cycle...")
        result = asyncio.run(runner.run_single_cycle())
        decisions = result.get("trade_decisions", [])
        trades = [d for d in decisions if d["action"] != "hold"]
        console.print(f"\nCycle complete: {len(trades)} trades decided")
        for t in trades:
            console.print(f"  {t['action'].upper()} {t['symbol']} x{t['quantity']}")
    else:
        try:
            asyncio.run(runner.run())
        except KeyboardInterrupt:
            console.print("\n👋 Stockbot stopped")


if __name__ == "__main__":
    app()
