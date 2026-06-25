"""Streamlit dashboard for AI Capacity Optimizer."""

from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from aco.backend.api_gateway import provider_pool_summary
from aco.backend.predictor import DEFAULT_DATA_DIR, generate_prediction_report


def risk_badge(value: str) -> str:
    colors = {
        "green": "#0f766e",
        "yellow": "#a16207",
        "red": "#b91c1c",
    }
    color = colors.get(value, "#334155")
    return f"<span style='color:{color};font-weight:700'>{value.upper()}</span>"


def main() -> None:
    st.set_page_config(page_title="AI Capacity Optimizer", layout="wide")
    st.title("AI Capacity Optimizer")

    report = generate_prediction_report(data_dir=DEFAULT_DATA_DIR)
    forecast = report["forecast"]
    idle = report["idle"]
    optimizer = report["optimizer"]
    relay = report["relay"]
    allocation = relay["allocation"]
    capacity = provider_pool_summary(data_dir=DEFAULT_DATA_DIR)

    cols = st.columns(5)
    cols[0].metric("Current Usage", f"{forecast['current_usage']:,}", f"{forecast['usage_percent']}%")
    cols[1].metric("Month-End Forecast", f"{forecast['predicted_month_end_usage']:,}", f"{forecast['predicted_month_end_percent']}%")
    cols[2].metric("Idle Tokens", f"{forecast['estimated_idle_tokens']:,}")
    cols[3].metric("Relay Allocated", f"{allocation['allocated_tokens']:,}", f"{allocation['coverage_percent']}%")
    cols[4].metric("Virtual Credits", f"{optimizer['task_injection']['virtual_credits']:,}")

    st.markdown(
        f"Idle risk: {risk_badge(idle['idle_risk'])} &nbsp;&nbsp; Usage risk: {risk_badge(idle['usage_risk'])}",
        unsafe_allow_html=True,
    )

    history = report["daily_history"]
    chart_data = {item["date"]: item["tokens"] for item in history}
    st.line_chart(chart_data)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Optimization Suggestions")
        for suggestion in optimizer["suggestions"]:
            st.write(f"- {suggestion}")

    with right:
        st.subheader("Task Injection Simulation")
        selected_tasks = optimizer["task_injection"]["selected_tasks"]
        if selected_tasks:
            st.dataframe(selected_tasks, hide_index=True, width="stretch")
        else:
            st.write("No tasks selected.")

    st.subheader("Relay Hub")
    hub_cols = st.columns(4)
    hub_cols[0].metric("Active Requests", f"{relay['active_request_count']:,}")
    hub_cols[1].metric("Requested Tokens", f"{allocation['requested_tokens']:,}")
    hub_cols[2].metric("Remaining Capacity", f"{allocation['remaining_tokens']:,}")
    hub_cols[3].metric("Pressure Index", f"{allocation['pressure_index']}")

    relay_left, relay_right = st.columns([1, 1])
    with relay_left:
        st.write("Allocated Requests")
        if allocation["selected_requests"]:
            st.dataframe(allocation["selected_requests"], hide_index=True, width="stretch")
        else:
            st.write("No relay requests allocated.")

    with relay_right:
        st.write("Skipped Requests")
        if allocation["skipped_requests"]:
            st.dataframe(allocation["skipped_requests"], hide_index=True, width="stretch")
        else:
            st.write("No relay requests skipped.")

    st.subheader("Unified API")
    api_cols = st.columns(3)
    api_cols[0].metric("Providers", f"{len(capacity['providers']):,}")
    api_cols[1].metric("Total Remaining Tokens", f"{capacity['total_remaining_tokens']:,}")
    api_cols[2].metric("Default Endpoint", "/v1/chat/completions")
    st.dataframe(capacity["providers"], hide_index=True, width="stretch")

    st.subheader("Forecast Report")
    st.json(report)


if __name__ == "__main__":
    main()
