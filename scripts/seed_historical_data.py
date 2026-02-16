#!/usr/bin/env python3
"""One-time script to download and store historical market data."""

from datetime import datetime, timedelta

import typer
from rich.console import Console
from rich.progress import track

app = typer.Typer(help="Seed historical market data")
console = Console()


@app.command()
def seed(
    symbols: str = typer.Option("AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,JPM,V,UNH", help="Symbols"),
    days: int = typer.Option(365, help="Days of history to download"),
    timeframe: str = typer.Option("1day", help="Timeframe: 1min, 5min, 15min, 1hour, 1day"),
):
    """Download historical data and store in DuckDB."""
    from config.settings import Settings
    from stockbot.broker.client import AlpacaClient
    from stockbot.data.market_data import MarketDataService
    from stockbot.data.storage import MarketDataStore

    settings = Settings()
    broker = AlpacaClient(settings)
    data_svc = MarketDataService(broker.data_client)
    store = MarketDataStore(settings.duckdb_path)

    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    end = datetime.now()
    start = end - timedelta(days=days)

    console.print(f"\n📥 Downloading {days} days of {timeframe} data")
    console.print(f"   Symbols: {', '.join(symbol_list)}\n")

    for symbol in track(symbol_list, description="Downloading..."):
        try:
            df = data_svc.get_bars(symbol, timeframe=timeframe, start=start, end=end)
            rows = store.save_bars(symbol, timeframe, df)
            console.print(f"  ✓ {symbol}: {rows} bars saved")
        except Exception as e:
            console.print(f"  ✗ {symbol}: {e}", style="red")

    store.close()
    console.print(f"\n✅ Data stored in {settings.duckdb_path}")


if __name__ == "__main__":
    app()
