# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

st.markdown("""
    <style>
        .css-1kyxreq > div > div {
            gap: 100px !important;  /* Adjust the number as needed */
        }
    </style>
""", unsafe_allow_html=True)

# === 2. Cached CSV Loader ===
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df['Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    return df

# === 3. Team Selector ===
available_teams = ["U15", "U16", "U17", "U19"]
selected_team = st.selectbox("Select Team", available_teams)

if selected_team:
    filename = f"Player Data/{selected_team}_PD_Data.csv"

    if not os.path.exists(filename):
        st.error(f"File {filename} not found.")
        st.stop()

    df = load_data(filename)

# === 4. Filter and Sort ===
df = df.dropna(subset=["Date", "Session Type", "Athlete Name", "Segment Name"])
df = df[df["Segment Name"] == "Whole Session"]
df = df.sort_values("Date")

# === 5. Define Metrics ===
metrics = ["Distance (m)", "High Intensity Running (m)", "Sprint Distance (m)",
           "No. of Sprints", "Top Speed (kph)", "Accelerations", "Decelerations"]

players = df["Athlete Name"].unique()
st.title(f"{selected_team} Player Readiness Dashboard")

# === 5.1 Show Latest Match Date ===
all_match_data = df[df["Session Type"] == "Match Session"]
if not all_match_data.empty:
    latest_overall_match_date = all_match_data["Date"].max().date()
    st.markdown(f"**Latest Match Date Used:** `{latest_overall_match_date}`")
else:
    st.markdown("**Latest Match Date Used:** _None found in dataset_")

# === Helper: Assign color based on ratio ===
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

# === Helper: Create gauge chart ===
def create_readiness_gauge(train_val, match_val, metric_name):
    if pd.isna(match_val) or match_val == 0:
        ratio = 0
    else:
        ratio = train_val / match_val

    bar_color = get_color(ratio)
    axis_max = max(1.5, ratio)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",  # ✅ FIXED: removed 'title'
        value=round(ratio, 2),
        number={"suffix": "", "font": {"size": 16}},  # shows 2.14 instead of percent
        title={"text": metric_name, "font": {"size": 16}},  # metric name at top
        gauge={
            "axis": {
                "range": [0, axis_max],
                "tickwidth": 0,
                "showticklabels": False
            },
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
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=180,
    )
    return fig

# === 6. Loop Over Players ===
valid_players = 0

for player in players:
    player_data = df[df["Athlete Name"] == player]

    match_data = player_data[player_data["Session Type"] == "Match Session"]
    training_data = player_data[player_data["Session Type"] == "Training Session"]

    if match_data.empty:
        continue

    # Get most recent match
    latest_match = match_data.iloc[-1]
    match_date = latest_match["Date"]

    # Get 3 trainings after the latest match
    post_match_train = training_data[training_data["Date"] > match_date].head(3)

    if post_match_train.empty:
        continue

    st.markdown(f"### {player}")
    cols = st.columns(len(metrics))
    valid_players += 1


    for i, metric in enumerate(metrics):
        match_val = latest_match.get(metric, 0)
        train_val = post_match_train[metric].sum()

        fig = create_readiness_gauge(train_val, match_val, metric)

        with cols[i]:
            st.plotly_chart(fig, use_container_width=True, key=f"{player}-{metric}")

# === 7. If no valid players found ===
if valid_players == 0:
    st.warning("No players have a match followed by training sessions.")
