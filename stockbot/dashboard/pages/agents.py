"""Dashboard agents page - agent decision audit trail."""

import json

import streamlit as st
import pandas as pd

from stockbot.db.session import init_db, get_engine


def render():
    st.title("Agent Decisions")

    try:
        init_db()
        engine = get_engine()

        decisions_df = pd.read_sql(
            "SELECT * FROM agent_decisions ORDER BY created_at DESC LIMIT 200", engine
        )

        if decisions_df.empty:
            st.info("No agent decisions recorded yet. Start the bot to see agent reasoning.")
            return

        # Filter by cycle
        cycles = sorted(decisions_df["cycle_id"].unique(), reverse=True)
        selected_cycle = st.selectbox("Trading Cycle", cycles)

        cycle_decisions = decisions_df[decisions_df["cycle_id"] == selected_cycle]

        # Display by agent
        for agent_name in ["market_analyst", "risk_manager", "portfolio_manager"]:
            agent_decisions = cycle_decisions[cycle_decisions["agent_name"] == agent_name]
            if agent_decisions.empty:
                continue

            st.subheader(_format_agent_name(agent_name))

            for _, row in agent_decisions.iterrows():
                with st.expander(f"{row['symbol']} - {_extract_action(row['output_data'])}"):
                    st.markdown(f"**Reasoning:** {row['reasoning']}")

                    # Parse and display output data
                    try:
                        output = json.loads(row["output_data"])
                        st.json(output)
                    except (json.JSONDecodeError, TypeError):
                        st.text(row["output_data"])

                    st.caption(f"Time: {row['created_at']}")

    except Exception as e:
        st.error(f"Error loading agent decisions: {e}")


def _format_agent_name(name: str) -> str:
    return name.replace("_", " ").title()


def _extract_action(output_data: str) -> str:
    try:
        data = json.loads(output_data)
        if "recommendation" in data:
            return data["recommendation"]
        if "approved" in data:
            return "Approved" if data["approved"] else "Rejected"
        if "action" in data:
            return data["action"]
    except (json.JSONDecodeError, TypeError):
        pass
    return ""
