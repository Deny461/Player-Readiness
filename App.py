# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
from datetime import timedelta
import streamlit as st

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
players = sorted(df["Athlete Name"].dropna().unique())

# 🔁 Use same training week for all players
global_training_df = df[df["Session Type"] == "Training Session"]
latest_training_date = global_training_df["Date"].max()
st.write("🌐 Global Latest Training Date:", latest_training_date)
if pd.isna(latest_training_date):
    st.warning("No training sessions found in dataset.")
    st.stop()

iso_year, iso_week, _ = latest_training_date.isocalendar()
week_start = latest_training_date - timedelta(days=latest_training_date.weekday())
match_cutoff_date = week_start - timedelta(days=1)

for player in players:
    player_data = df[df["Athlete Name"] == player].copy()
    player_data["Duration (mins)"] = pd.to_numeric(player_data["Duration (mins)"], errors="coerce")
    for m in metrics:
        player_data[m] = pd.to_numeric(player_data[m], errors="coerce")

    matches = player_data[
        (player_data["Session Type"] == "Match Session") &
        (player_data["Date"] <= match_cutoff_date) &
        (player_data["Duration (mins)"] > 0)
    ].sort_values("Date")

    if matches.empty:
        continue

    training_week = player_data[
        (player_data["Session Type"] == "Training Session") &
        (player_data["Date"].apply(lambda d: d.isocalendar()[:2] == (iso_year, iso_week)))
    ]

    if training_week.empty:
        continue

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

    player_data["Week"] = player_data["Date"].dt.isocalendar().week
    player_data["Weekday"] = player_data["Date"].dt.day_name()

    st.markdown(f"### {player}")
    cols = st.columns(len(metrics))
    valid_players += 1

    for i, metric in enumerate(metrics):
        if metric == "Top Speed (kph)":
            train_val = grouped_trainings[metric].max()
            benchmark = top_speed_benchmark
        else:
            train_val = grouped_trainings[metric].sum()
            benchmark = match_avg.get(metric, None)

        label = metric_labels[metric]
        fig = create_readiness_gauge(train_val, benchmark, label)

        with cols[i]:
            st.markdown(f"<div style='text-align: center; font-weight: bold;'>{label}</div>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, key=f"{player}-{metric}")

            flag = ""
            if metric != "Top Speed (kph)":
                weekday_avgs = player_data[
                    (player_data["Session Type"] == "Training Session")
                ].groupby("Weekday")[metric].mean()

                current_weekdays = training_week["Date"].dt.day_name().tolist()
                current_day = latest_training_date.day_name()
                current_sum = training_week[metric].sum()
                thursday_done = "Thursday" in current_weekdays

                if not thursday_done:
                    projected_total = sum([weekday_avgs.get(day, 0) for day in ["Tuesday", "Wednesday", "Thursday"]])
                    flag_val = projected_total
                else:
                    flag_val = current_sum

                # Get ISO week and year of the current week
iso_current = latest_training_date.isocalendar()
current_week = iso_current.week
current_year = iso_current.year

# Get previous week (handling wrap around new year)
if current_week == 1:
    prev_week = 52
    prev_year = current_year - 1
else:
    prev_week = current_week - 1
    prev_year = current_year

# Filter for previous week's data
player_data["Year"] = player_data["Date"].dt.isocalendar().year
previous_week_data = player_data[
    (player_data["Session Type"] == "Training Session") &
    (player_data["Date"].dt.isocalendar().week == prev_week) &
    (player_data["Date"].dt.isocalendar().year == prev_year)
]

# Sum metric for previous week
previous_week_total = previous_week_data[metric].sum()

if previous_week_total > 0 and flag_val > 1.10 * previous_week_total:
                flag = "⚠️" if thursday_done else "🔮⚠️"

                st.markdown(
                    f"<div style='text-align: center; font-size: 14px; color: gray;'>{train_val:.1f} / {benchmark:.1f} = {train_val / benchmark:.2f} {flag}</div>",
                    unsafe_allow_html=True
                )

                debug_lines = [
            f"<b>📊 Flag Debug for {label}:</b>",
            f"• Previous Week Total: {previous_week_total:.1f}",
            f"• Current Week Total: {current_sum:.1f}",
            f"• Projected Week Total: {projected_total:.1f}",
            f"• Value Used: {'Actual' if thursday_done else 'Projected'} = {flag_val:.1f}",
            f"• Threshold (110%): {(1.10 * previous_week_total):.1f}",
        f"• ⚠️ Flag: {'YES' if flag else 'NO'}"
]