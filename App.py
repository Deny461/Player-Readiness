# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

import streamlit as st

st.set_page_config(layout="wide")

# === LOGO HEADER (Row 1) ===
with st.container():
    col1, col2, col3 = st.columns([0.05, 0.002, 0.52])  # Keep it tight
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

col_spacer, colA, colB, col_spacer2 = st.columns([0.1, .1, .6, 2])  # Centered with minimal gap
with colA:
    if st.button("Continue"):
        st.session_state.proceed = True
        st.rerun()

with colB:
    if st.button("Back"):
        st.session_state.proceed = False
        st.rerun()

# === 5. Stop Until Proceed ===
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

# === 7. Latest Match Date ===
match_df = df[df["Session Type"] == "Match Session"]
if not match_df.empty:
    latest_match_date = match_df["Date"].max().date()
    st.markdown(f"**Latest Match Date Used:** `{latest_match_date}`")
else:
    st.markdown("**Latest Match Date Used:** _None found in dataset_")

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
    if ratio < 0.5:
        return "red"
    elif ratio < 0.75:
        return "orange"
    elif ratio < 1.0:
        return "yellow"
    elif ratio <= 1.30:
        return "green"
    else:
        return "black"

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
valid_players = 0
players = df["Athlete Name"].unique()

for player in players:
    player_data = df[df["Athlete Name"] == player]
    matches = player_data[player_data["Session Type"] == "Match Session"].sort_values("Date")
    if matches.empty:
        continue

    latest_match = matches.iloc[-1]
    match_cutoff_date = latest_match["Date"]
    match_games = matches[matches["Date"] <= match_cutoff_date]
    if match_games.empty:
        continue

    # Match average per 90 mins
    match_avg = {
        m: (match_games[m] / match_games["Duration (mins)"] * 90).mean()
        for m in metrics if m != "Top Speed (kph)"
    }
    top_speed_benchmark = player_data["Top Speed (kph)"].max()

    # Training after last match
    trainings = player_data[
        (player_data["Session Type"] == "Training Session") &
        (player_data["Date"] > match_cutoff_date)
    ].sort_values("Date").head(3)

    if trainings.empty:
        continue

    st.markdown(f"### {player}")
    cols = st.columns(len(metrics))
    valid_players += 1

    for i, metric in enumerate(metrics):
        if metric == "Top Speed (kph)":
            train_val = trainings[metric].max()
            benchmark = top_speed_benchmark
        else:
            total = trainings[metric].sum()
            minutes = trainings["Duration (mins)"].sum()
            train_val = (total / minutes) * 90 if minutes > 0 else 0
            benchmark = match_avg[metric]

        label = metric_labels[metric]
        fig = create_readiness_gauge(train_val, benchmark, label)
        with cols[i]:
            st.markdown(f"<div style='text-align: center; font-weight: bold;'>{label}</div>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, key=f"{player}-{metric}")

# === 11. No Valid Players Warning ===
if valid_players == 0:
    st.warning("No players have a match followed by training sessions.")
