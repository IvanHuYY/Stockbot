"""Application settings loaded from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Alpaca
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    paper_trading: bool = True

    # LLM
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = 0.1

    # Trading
    trading_cycle_minutes: int = 15
    max_position_pct: float = 0.05
    max_portfolio_risk_pct: float = 0.20
    max_daily_loss_pct: float = 0.03

    # Data
    duckdb_path: str = "data/stockbot.duckdb"

    # Logging
    log_level: str = "INFO"
