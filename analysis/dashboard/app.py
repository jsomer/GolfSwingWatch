from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import load_features

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from movement_viz import find_swing, load_raw_swings, movement_catalog, movement_payload

st.set_page_config(
    page_title="GolfSwingWatch Analysis",
    page_icon=":golf:",
    layout="wide",
)

st.title("GolfSwingWatch Data Analysis")
st.caption("Interactive browser dashboard for swing feature exploration.")

with st.sidebar:
    st.header("Data Source")
    data_path = st.text_input(
        "Feature table path (optional)",
        value="",
        help="If empty, defaults to analysis/output/swing_features.parquet then csv.",
    )

    st.header("Filters")

try:
    df = load_features(data_path.strip() or None)
except Exception as exc:  # noqa: BLE001
    st.error(str(exc))
    st.info("Run: python analysis/analyze_swings.py --input <path> --output-dir analysis/output")
    st.stop()

clubs = sorted([c for c in df.get("club", []).dropna().unique()]) if "club" in df.columns else []
ratings = sorted([int(r) for r in df.get("rating", []).dropna().unique()]) if "rating" in df.columns else []

with st.sidebar:
    selected_clubs = st.multiselect("Club", clubs, default=clubs)
    selected_ratings = st.multiselect("Rating", ratings, default=ratings)
    if "date_only" in df.columns and not df["date_only"].dropna().empty:
        min_date = df["date_only"].dropna().min()
        max_date = df["date_only"].dropna().max()
        selected_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        selected_range = None

filtered = df.copy()
if selected_clubs and "club" in filtered.columns:
    filtered = filtered[filtered["club"].isin(selected_clubs)]
if selected_ratings and "rating" in filtered.columns:
    filtered = filtered[filtered["rating"].isin(selected_ratings)]
if selected_range and "date_only" in filtered.columns:
    start_date, end_date = selected_range
    filtered = filtered[
        (filtered["date_only"] >= start_date) & (filtered["date_only"] <= end_date)
    ]

if filtered.empty:
    st.warning("No records match the current filter selection.")
    st.stop()

total_swings = len(filtered)
avg_rating = filtered["rating"].mean() if "rating" in filtered.columns else None
avg_tempo = filtered["tempo_ratio"].mean() if "tempo_ratio" in filtered.columns else None
avg_peak_rotation = (
    filtered["peak_rotational_velocity"].mean()
    if "peak_rotational_velocity" in filtered.columns
    else None
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Swings", f"{total_swings:,}")
col2.metric("Average Rating", f"{avg_rating:.2f}" if avg_rating is not None else "n/a")
col3.metric("Average Tempo Ratio", f"{avg_tempo:.2f}" if avg_tempo is not None else "n/a")
col4.metric(
    "Avg Peak Rotation",
    f"{avg_peak_rotation:.2f}" if avg_peak_rotation is not None else "n/a",
)

left, right = st.columns(2)

with left:
    if "date" in filtered.columns and "tempo_ratio" in filtered.columns:
        trend = (
            filtered.dropna(subset=["date"])
            .sort_values("date")
            .groupby("date_only", as_index=False)["tempo_ratio"]
            .mean()
        )
        fig = px.line(
            trend,
            x="date_only",
            y="tempo_ratio",
            markers=True,
            title="Tempo Ratio Trend",
            labels={"date_only": "Date", "tempo_ratio": "Tempo Ratio"},
        )
        st.plotly_chart(fig, use_container_width=True)

with right:
    if "peak_rotational_velocity" in filtered.columns and "club" in filtered.columns:
        fig = px.box(
            filtered,
            x="club",
            y="peak_rotational_velocity",
            color="club",
            title="Peak Rotational Velocity by Club",
            labels={"club": "Club", "peak_rotational_velocity": "Peak Rotational Velocity"},
        )
        st.plotly_chart(fig, use_container_width=True)

bottom_left, bottom_right = st.columns(2)

with bottom_left:
    if "rating" in filtered.columns:
        fig = px.histogram(
            filtered,
            x="rating",
            nbins=10,
            title="Rating Distribution",
            labels={"rating": "Rating"},
        )
        st.plotly_chart(fig, use_container_width=True)

with bottom_right:
    if "swing_plane_stability" in filtered.columns and "club" in filtered.columns:
        stability = filtered.groupby("club", as_index=False)["swing_plane_stability"].mean()
        fig = px.bar(
            stability,
            x="club",
            y="swing_plane_stability",
            color="club",
            title="Average Swing Plane Stability by Club",
            labels={"club": "Club", "swing_plane_stability": "Stability"},
        )
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Filtered Data")
st.dataframe(filtered, use_container_width=True, hide_index=True)

st.subheader("Movement Explorer (Plotly)")
st.caption("Inspect how acceleration, rotation, and orientation change during a recorded swing.")

raw_path = st.text_input(
    "Raw swing export path (optional)",
    value="",
    help="Defaults to data/raw/swings.json",
)

try:
    raw_records = load_raw_swings(raw_path.strip() or None)
    catalog = movement_catalog(raw_records)
except Exception as exc:  # noqa: BLE001
    st.info(f"Movement traces unavailable: {exc}")
else:
    if not catalog:
        st.warning("No swings with samples found in raw export.")
    else:
        labels = {
            item["id"]: f"{item['club']} • {str(item['date'])[:19]} • {item['sample_count']} samples"
            for item in catalog
        }
        selected_id = st.selectbox("Swing", options=list(labels.keys()), format_func=lambda key: labels[key])
        payload = movement_payload(find_swing(raw_records, selected_id) or {})
        series = payload["series"]
        markers = payload["event_markers"]

        def _add_markers(fig: go.Figure, ymax: float) -> None:
            colors = {"start": "green", "impact": "red", "followThrough": "blue"}
            for marker in markers:
                fig.add_vline(
                    x=marker["time"],
                    line_dash="dash",
                    line_color=colors.get(marker["type"], "gray"),
                    annotation_text=marker["type"],
                )

        if series["times"]:
            accel_fig = go.Figure()
            accel_fig.add_trace(
                go.Scatter(x=series["times"], y=series["accel_mag"], mode="lines", name="Acceleration")
            )
            _add_markers(accel_fig, max(series["accel_mag"]) if series["accel_mag"] else 1)
            accel_fig.update_layout(title="Acceleration Magnitude", xaxis_title="Seconds", yaxis_title="g")
            st.plotly_chart(accel_fig, use_container_width=True)

            gyro_fig = go.Figure()
            gyro_fig.add_trace(
                go.Scatter(x=series["times"], y=series["gyro_mag"], mode="lines", name="Rotation")
            )
            _add_markers(gyro_fig, max(series["gyro_mag"]) if series["gyro_mag"] else 1)
            gyro_fig.update_layout(title="Rotational Velocity Magnitude", xaxis_title="Seconds", yaxis_title="rad/s")
            st.plotly_chart(gyro_fig, use_container_width=True)

            attitude_fig = go.Figure()
            attitude_fig.add_trace(go.Scatter(x=series["times"], y=series["pitch"], mode="lines", name="Pitch"))
            attitude_fig.add_trace(go.Scatter(x=series["times"], y=series["roll"], mode="lines", name="Roll"))
            attitude_fig.add_trace(go.Scatter(x=series["times"], y=series["yaw"], mode="lines", name="Yaw"))
            _add_markers(attitude_fig, 1)
            attitude_fig.update_layout(title="Watch Orientation", xaxis_title="Seconds", yaxis_title="Radians")
            st.plotly_chart(attitude_fig, use_container_width=True)
        else:
            st.warning("Selected swing has no sample data.")
