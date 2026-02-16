"""Streamlit dashboard - main app entry point."""

import streamlit as st

st.set_page_config(
    page_title="Stockbot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar navigation
st.sidebar.title("Stockbot")
st.sidebar.markdown("AI-Powered Trading Bot")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Trades", "Agent Decisions", "Backtest", "Settings"],
    index=0,
)

if page == "Overview":
    from stockbot.dashboard.pages.overview import render

    render()
elif page == "Trades":
    from stockbot.dashboard.pages.trades import render

    render()
elif page == "Agent Decisions":
    from stockbot.dashboard.pages.agents import render

    render()
elif page == "Backtest":
    from stockbot.dashboard.pages.backtest import render

    render()
elif page == "Settings":
    from stockbot.dashboard.pages.settings import render

    render()
