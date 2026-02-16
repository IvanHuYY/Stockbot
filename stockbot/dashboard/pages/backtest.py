"""Dashboard backtest page - run and view backtest results."""

from datetime import datetime

import streamlit as st


def render():
    st.title("Backtesting")

    st.subheader("Run a Backtest")

    col1, col2 = st.columns(2)
    with col1:
        strategy = st.selectbox("Strategy", ["momentum", "mean_reversion", "composite"])
        symbols = st.text_input("Symbols (comma-separated)", "AAPL,MSFT,GOOGL")
        capital = st.number_input("Initial Capital ($)", value=100000, step=10000)

    with col2:
        start_date = st.date_input("Start Date", datetime(2024, 1, 1))
        end_date = st.date_input("End Date", datetime(2024, 12, 31))

    if st.button("Run Backtest", type="primary"):
        symbol_list = [s.strip().upper() for s in symbols.split(",")]

        with st.spinner(f"Running {strategy} backtest..."):
            try:
                from stockbot.backtesting.engine import BacktestConfig, BacktestEngine

                config = BacktestConfig(
                    symbols=symbol_list,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.min.time()),
                    initial_capital=capital,
                    strategy_name=strategy,
                )
                engine = BacktestEngine(config)
                result = engine.run()

                # Display metrics
                st.subheader("Results")
                m = result.metrics

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Return", f"{m['total_return']:.2%}")
                col2.metric("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}")
                col3.metric("Max Drawdown", f"{m['max_drawdown']:.2%}")
                col4.metric("Win Rate", f"{m['win_rate']:.1%}")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Annual Return", f"{m['annualized_return']:.2%}")
                col2.metric("Sortino Ratio", f"{m['sortino_ratio']:.2f}")
                col3.metric("Profit Factor", f"{m['profit_factor']:.2f}")
                col4.metric("Total Trades", m["num_trades"])

                # Equity curve
                if not result.equity_curve.empty:
                    st.subheader("Equity Curve")
                    st.line_chart(result.equity_curve)

                # Trade log
                if result.trades:
                    st.subheader("Trades")
                    import pandas as pd
                    trades_df = pd.DataFrame(result.trades)
                    st.dataframe(trades_df, use_container_width=True)

            except Exception as e:
                st.error(f"Backtest failed: {e}")
