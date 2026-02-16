# Stockbot

AI-powered autonomous stock trading bot using LangGraph agents and Alpaca.

## Architecture

```
Data Loader → Market Analyst → Risk Manager → Portfolio Manager → Executor → Reporter
```

Three LLM-based agents communicate via shared state in a LangGraph pipeline:
- **Market Analyst**: Analyzes technical indicators, support/resistance levels, and news sentiment
- **Risk Manager**: Enforces hard risk limits (position sizing, stop-loss, portfolio risk)
- **Portfolio Manager**: Makes final buy/sell/hold decisions with order parameters

## Quick Start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Edit .env with your Alpaca and Anthropic API keys

# 3. Run (paper trading)
python scripts/run_bot.py

# 4. Dashboard
make dashboard
```

## Commands

| Command | Description |
|---------|-------------|
| `python scripts/run_bot.py` | Start the trading bot (paper mode by default) |
| `python scripts/run_bot.py --single` | Run one trading cycle and exit |
| `python scripts/run_backtest.py` | Run a backtest |
| `python scripts/run_backtest.py compare` | Compare multiple strategies |
| `python scripts/seed_historical_data.py` | Download historical data |
| `make dashboard` | Launch Streamlit dashboard on port 8501 |
| `make test` | Run tests |

## Project Structure

```
stockbot/
├── broker/          # Alpaca API integration (orders, positions, account)
├── data/            # Market data, storage (DuckDB), features, news
├── agents/          # LangGraph agent pipeline
│   ├── tools/       # LangChain tools (technical analysis, risk, sentiment)
│   ├── prompts/     # System prompts for each agent
│   └── graph.py     # StateGraph definition
├── strategies/      # Rule-based strategies (momentum, mean reversion)
├── backtesting/     # Backtest engine, metrics, reports, comparison
├── dashboard/       # Streamlit monitoring UI
├── engine/          # Trading loop, scheduler, event bus
├── db/              # Database models (trades, decisions, equity)
└── utils/           # Market hours, decorators, formatters
```

## Risk Management

Hard-coded safety limits enforced by code (not just LLM reasoning):
- Max 5% of equity per position
- Max 20% total portfolio risk
- Min 2:1 risk/reward ratio on every trade
- Trading halted if daily loss exceeds 3%
- Paper trading mode by default

## Docker

```bash
docker-compose up  # Runs bot + dashboard
```
