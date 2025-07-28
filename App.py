# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
from datetime import timedelta

st.set_page_config(
    page_title="Player Readiness",
    page_icon="BostonBoltsLogo.png",
    layout="wide"
)

# === LOGO HEADER (Row 1) ===
with st.container():
    col1, col2, col3 = st.columns([0.05, 0.002, 0.52])
    with col1:
        st.image("BostonBoltsLogo.png", width=220)
    with col2:
        st.markdown("<div style='border-left:2px solid gray; height:180px;'></div>", unsafe_allow_html=True)
    with col3:
        st.image("MLSNextLogo.png", width=220)

# === TITLE SECTION (Row 2) ===
with st.container():
    st.markdown("""
        <h1 style='text-align: center; font-size: 72px; margin-top: -60px;'>Player Readiness</h1>
    """, unsafe_allow_html=True)

# === 2. Cached CSV Loader ===
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    # Try US format first
    df['Date'] = pd.to_datetime(df['Start Date'], format='%m/%d/%y', errors='coerce')
    if df['Date'].isna().all():
        df['Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    return df

# === 3. Session Control ===
if "proceed" not in st.session_state:
    st.session_state.proceed = False

st.markdown("###")

available_teams = [
    "U15 MLS Next", "U16 MLS Next", "U17 MLS Next", "U19 MLS Next",
    "U15 MLS Next 2", "U16 MLS Next 2", "U17 MLS Next 2", "U19 MLS Next 2"
]
selected_team = st.selectbox("Select Team", available_teams)

col_spacer, colA, colB, col_spacer2 = st.columns([0.0001, 0.1, 1.5, 1])
with colA:
    if st.button("Continue"):
        st.session_state.proceed = True
        st.rerun()

with colB:
    if st.button("Back"):
        st.session_state.proceed = False
        st.rerun()

if not st.session_state.proceed:
    st.stop()

# === 6. Load and Clean Data ===
filename = f"Player Data/{selected_team}_PD_Data.csv"
if not os.path.exists(filename):
    st.error(f"File {filename} not found.")
    st.stop()

df = load_data(filename)
df = df.dropna(subset=["Date", "Session Type", "Athlete Name", "Segment Name"])
df = df[df["Segment Name"] == "Whole Session"]
df = df.sort_values("Date")

# === 7. Anchor to Latest Match Week ===
match_df = df[df["Session Type"] == "Match Session"]
if not match_df.empty:
    latest_match_date = match_df["Date"].max()
    st.markdown(f"**Latest Match Date Used:** `{latest_match_date.date()}`")
    iso_year, iso_week, _ = latest_match_date.isocalendar()
else:
    st.markdown("**Latest Match Date Used:** _None found in dataset_")
    st.stop()

# === 8. Metric Setup ===
metrics = ["Distance (m)", "High Intensity Running (m)", "Sprint Distance (m)", "No. of Sprints", "Top Speed (kph)"]
metric_labels = {
    "Distance (m)": "Total Distance",
    "High Intensity Running (m)": "HSR",
    "Sprint Distance (m)": "Sprint Distance",
    "No. of Sprints": "# of Sprints",
    "Top Speed (kph)": "Top Speed"
}

# === 9. Helper Functions ===
def get_color(ratio):
    if ratio < 0.5: return "red"
    elif ratio < 0.75: return "orange"
    elif ratio < 1.0: return "yellow"
    elif ratio <= 1.30: return "green"
    else: return "black"

def create_readiness_gauge(value, benchmark, label):
    ratio = 0 if pd.isna(benchmark) or benchmark == 0 else value / benchmark
    bar_color = get_color(ratio)
    axis_max = max(1.5, ratio)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(ratio, 2),
        number={"font": {"size": 20}},
        gauge={
            "axis": {"range": [0, axis_max], "tickwidth": 0, "showticklabels": False},
            "bar": {"color": bar_color},
            "steps": [
                {"range": [0, 0.5], "color": "#ffcccc"},
                {"range": [0.5, 0.75], "color": "#ffe0b3"},
                {"range": [0.75, 1.0], "color": "#ffffcc"},
                {"range": [1.0, 1.3], "color": "#ccffcc"},
                {"range": [1.3, axis_max], "color": "#e6e6e6"},
            ]
        }
    ))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=180)
    return fig

# === 10. Render Gauges Per Player ===
players = sorted(df["Athlete Name"].dropna().unique())

for player in players:
    player_data = df[df["Athlete Name"] == player].copy()
    player_data["Duration (mins)"] = pd.to_numeric(player_data["Duration (mins)"], errors="coerce")
    for m in metrics:
        player_data[m] = pd.to_numeric(player_data[m], errors="coerce")

    matches = player_data[
        (player_data["Session Type"] == "Match Session") &
        (player_data["Date"] <= latest_match_date) &
        (player_data["Duration (mins)"] > 0)
    ].sort_values("Date")
    if matches.empty:
        continue

    # Force all into latest match week
    iso_vals = player_data["Date"].dt.isocalendar()
    training_week = player_data[
        (player_data["Session Type"] == "Training Session") &
        (iso_vals["week"] == iso_week) &
        (iso_vals["year"] == iso_year)
    ]

    # Inject dummy row if no training exists in that week
    if training_week.empty:
        training_week = pd.DataFrame([{
            "Athlete Name": player,
            "Date": latest_match_date,
            "Session Type": "Training Session",
            "Segment Name": "Whole Session",
            "Distance (m)": 0,
            "High Intensity Running (m)": 0,
            "Sprint Distance (m)": 0,
            "No. of Sprints": 0,
            "Top Speed (kph)": 0,
            "Duration (mins)": 0
        }])

    # Compute match averages
    match_avg = {}
    for m in metrics:
        if m == "Top Speed (kph)":
            continue
        matches["Per90"] = matches[m] / matches["Duration (mins)"] * 90
        match_avg[m] = matches["Per90"].mean()

    top_speed_benchmark = player_data["Top Speed (kph)"].max()

    grouped_trainings = training_week.agg({
        "Distance (m)": "sum",
        "High Intensity Running (m)": "sum",
        "Sprint Distance (m)": "sum",
        "No. of Sprints": "sum",
        "Top Speed (kph)": "max"
    }).to_frame().T

    st.markdown(f"### {player}")
    cols = st.columns(len(metrics))

    for i, metric in enumerate(metrics):
        if metric == "Top Speed (kph)":
            train_val = grouped_trainings[metric].max()
            benchmark = top_speed_benchmark
        else:
            train_val = grouped_trainings[metric].sum()
            benchmark = match_avg.get(metric, None)

        fig = create_readiness_gauge(train_val, benchmark, metric_labels[metric])

        with cols[i]:
            st.markdown(f"<div style='text-align:center;font-weight:bold;'>{metric_labels[metric]}</div>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, key=f"{player}-{metric}")
