"""Interactive Streamlit command center backed by the incident domain model."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.domain import Severity
from app.main import INCIDENTS, metrics, priority_queue


def incident_frame() -> pd.DataFrame:
    """Return a presentation-ready snapshot without mutating the demo store."""
    return pd.DataFrame(
        [
            {
                "id": item.id,
                "title": item.title,
                "service": item.service,
                "severity": item.severity.value,
                "status": item.status.value,
                "owner": item.owner or "Unassigned",
                "sla_due_at": item.sla_due_at,
                "breached": item.breached,
            }
            for item in INCIDENTS.values()
        ]
    )


def main() -> None:
    st.set_page_config(page_title="Service Operations Command Center", page_icon="🛟", layout="centered")
    st.title("Service Operations Command Center")
    st.caption("SLA-aware incident visibility using fictional services, people, and operational events.")

    snapshot = metrics()
    first_row = st.columns(3)
    first_row[0].metric("Total", snapshot["total"])
    first_row[1].metric("Open", snapshot["open"])
    first_row[2].metric("Breached", snapshot["breached"])
    second_row = st.columns(2)
    second_row[0].metric("Resolved", snapshot["resolved"])
    second_row[1].metric("Unassigned", snapshot["unassigned"])

    incidents = incident_frame()
    st.subheader("Workload")
    filter_column, chart_column = st.columns((0.35, 0.65), gap="large")
    with filter_column:
        selected_severity = st.multiselect(
            "Severity",
            [item.value for item in Severity],
            default=[item.value for item in Severity],
        )
        show_breached_only = st.toggle("Breached only")
    with chart_column:
        status_counts = incidents.groupby("status").size().rename("incidents")
        st.bar_chart(status_counts, color="#2563EB")

    st.subheader("Priority queue")
    ordered_ids = [item["id"] for item in priority_queue()]
    queue = incidents[incidents["id"].isin(ordered_ids)].copy()
    queue["priority"] = queue["id"].map({identifier: position + 1 for position, identifier in enumerate(ordered_ids)})
    queue = queue[queue["severity"].isin(selected_severity)]
    if show_breached_only:
        queue = queue[queue["breached"]]
    queue = queue.sort_values("priority")
    st.dataframe(
        queue[["priority", "id", "title", "service", "severity", "owner", "sla_due_at", "breached"]],
        width="stretch",
        hide_index=True,
        column_config={
            "breached": st.column_config.CheckboxColumn("SLA breached"),
            "sla_due_at": st.column_config.DatetimeColumn("SLA due", format="MMM D, h:mm a"),
        },
    )

    st.subheader("Severity mix")
    severity_counts = incidents.groupby("severity").size().reindex([item.value for item in Severity], fill_value=0)
    st.bar_chart(severity_counts, color="#2563EB")

    with st.expander("Prototype boundary"):
        st.write(
            "The in-memory repository resets on restart. The X-Actor API header demonstrates attribution, "
            "not authentication; production use requires persistent storage, OIDC, and RBAC."
        )


if __name__ == "__main__":
    main()
