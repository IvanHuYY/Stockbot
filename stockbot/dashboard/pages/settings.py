"""Dashboard settings page - runtime configuration."""

import streamlit as st
import yaml
from pathlib import Path


def render():
    st.title("Settings")

    st.subheader("Trading Configuration")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Trading Mode", "Paper", disabled=True)
        st.number_input("Cycle Interval (minutes)", value=15, min_value=1, max_value=120)
        st.number_input("Max Position Size (%)", value=5, min_value=1, max_value=20)

    with col2:
        st.number_input("Max Portfolio Risk (%)", value=20, min_value=5, max_value=50)
        st.number_input("Max Daily Loss (%)", value=3, min_value=1, max_value=10)
        st.text_input("LLM Provider", "Anthropic", disabled=True)

    st.divider()

    # Watchlist
    st.subheader("Watchlist")
    watchlist_path = Path("config/symbols.yaml")
    if watchlist_path.exists():
        with open(watchlist_path) as f:
            data = yaml.safe_load(f)
            watchlist = data.get("watchlist", [])

        st.text_area(
            "Symbols (one per line)",
            "\n".join(watchlist),
            height=200,
            disabled=True,
            help="Edit config/symbols.yaml to change the watchlist",
        )
    else:
        st.warning("Watchlist config not found at config/symbols.yaml")

    st.divider()

    # Status
    st.subheader("System Status")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Bot Status:** Not connected (view only)")
        st.markdown("**Database:** SQLite (data/stockbot.db)")
    with col2:
        st.markdown("**Market Data:** DuckDB (data/stockbot.duckdb)")
        st.markdown("**Log Level:** INFO")

    st.info("To modify settings, edit the `.env` file and restart the bot.")
