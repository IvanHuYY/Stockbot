"""Dashboard overview page - portfolio summary and equity curve."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from stockbot.db.session import init_db, get_engine
from stockbot.utils.formatters import format_currency, format_pct


def render():
    st.title("Portfolio Overview")

    try:
        init_db()
        engine = get_engine()

        # Load equity snapshots
        eq_df = pd.read_sql("SELECT * FROM equity_snapshots ORDER BY timestamp", engine)

        if eq_df.empty:
            st.info("No data yet. Start the trading bot to see portfolio data.")
            _show_placeholder()
            return

        # Key metrics
        latest = eq_df.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Portfolio Value", format_currency(latest["portfolio_value"]))
        with col2:
            st.metric("Cash", format_currency(latest["cash"]))
        with col3:
            st.metric("Unrealized P&L", format_currency(latest["unrealized_pnl"]))
        with col4:
            st.metric("Positions", int(latest["num_positions"]))

        # Equity curve chart
        st.subheader("Equity Curve")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(eq_df["timestamp"]),
            y=eq_df["portfolio_value"],
            mode="lines",
            name="Portfolio Value",
            line=dict(color="#58a6ff", width=2),
        ))
        fig.update_layout(
            template="plotly_dark",
            height=400,
            yaxis_title="Value ($)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Recent trades
        st.subheader("Recent Trades")
        trades_df = pd.read_sql(
            "SELECT * FROM trades ORDER BY created_at DESC LIMIT 10", engine
        )
        if not trades_df.empty:
            st.dataframe(trades_df, use_container_width=True)
        else:
            st.info("No trades yet.")

    except Exception as e:
        st.error(f"Error loading data: {e}")
        _show_placeholder()


def _show_placeholder():
    st.markdown("""
    ### Getting Started
    1. Configure your API keys in `.env`
    2. Run `python scripts/run_bot.py` to start trading
    3. Data will appear here automatically
    """)
