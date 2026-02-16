"""Dashboard trades page - trade log and history."""

import streamlit as st
import pandas as pd

from stockbot.db.session import init_db, get_engine


def render():
    st.title("Trade Log")

    try:
        init_db()
        engine = get_engine()

        trades_df = pd.read_sql("SELECT * FROM trades ORDER BY created_at DESC", engine)

        if trades_df.empty:
            st.info("No trades recorded yet.")
            return

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            symbols = ["All"] + sorted(trades_df["symbol"].unique().tolist())
            selected_symbol = st.selectbox("Symbol", symbols)
        with col2:
            sides = ["All", "buy", "sell"]
            selected_side = st.selectbox("Side", sides)
        with col3:
            statuses = ["All"] + sorted(trades_df["status"].unique().tolist())
            selected_status = st.selectbox("Status", statuses)

        # Apply filters
        filtered = trades_df
        if selected_symbol != "All":
            filtered = filtered[filtered["symbol"] == selected_symbol]
        if selected_side != "All":
            filtered = filtered[filtered["side"] == selected_side]
        if selected_status != "All":
            filtered = filtered[filtered["status"] == selected_status]

        # Summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Trades", len(filtered))
        with col2:
            buys = len(filtered[filtered["side"] == "buy"])
            st.metric("Buys", buys)
        with col3:
            sells = len(filtered[filtered["side"] == "sell"])
            st.metric("Sells", sells)

        # Trade table
        st.dataframe(
            filtered[["created_at", "symbol", "side", "quantity", "order_type", "status", "reasoning"]],
            use_container_width=True,
            height=500,
        )

    except Exception as e:
        st.error(f"Error loading trades: {e}")
