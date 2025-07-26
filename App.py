# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

# === 2. Cached CSV Loader ===
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df['Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    return df

# === 3. Team Selector ===
available_teams = ["U15", "U16", "U17"]
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

        # Handle division by zero or NaN
        if pd.isna(match_val) or match_val == 0:
            readiness = 0
        else:
            readiness = (train_val / match_val) * 100
            readiness = round(min(readiness, 200), 1)

        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=readiness,
            number={'suffix': "%"},
            title={'text': metric, 'font': {'size': 12}},
            gauge={
                'axis': {'range': [0, 200], 'tickwidth': 1},
                'bar': {'color': "#2ECC71"},
                'steps': [
                    {'range': [0, 100], 'color': "#FFDDDD"},
                    {'range': [100, 150], 'color': "#FFE8B2"},
                    {'range': [150, 200], 'color': "#D4EDDA"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 100
                }
            }
        ))
        with cols[i]:
            st.plotly_chart(gauge, use_container_width=True, key=f"{player}-{metric}")

# === 7. If no valid players found ===
if valid_players == 0:
    st.warning("No players have a match followed by training sessions.")
