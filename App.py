# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os

# === 2. Cached CSV Loader ===
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df['Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    return df

# === 3. Team Selector ===
available_teams = ["U15", "U16", "U17"]  # or load from folder dynamically
selected_team = st.selectbox("Select Team", available_teams)

if selected_team:
    filename = f"PlayerData/{selected_team}_PD_Data.csv"

    if not os.path.exists(filename):
        st.error(f"File {filename} not found.")
        st.stop()

    df = load_data(filename)

# === 4. Clean and Sort Data ===
df = df.dropna(subset=["Date", "Session Type", "Athlete Name"])
df = df.sort_values("Date")

# === 5. Define Metrics ===
metrics = ["Distance (m)", "High Intensity Running (m)", "Sprint Distance (m)",
           "No. of Sprints", "Top Speed (kph)", "Accelerations", "Decelerations"]

players = df["Athlete Name"].unique()
st.title(f"{selected_team} Player Readiness Dashboard")

# Find the most recent match date across all players
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

    st.subheader(player)
    cols = st.columns(len(metrics))
    valid_players += 1

    for i, metric in enumerate(metrics):
        match_val = latest_match.get(metric)
        train_val = post_match_train[metric].sum()

        # Ensure no NaN or divide by zero
        if pd.isna(match_val) or match_val == 0:
            readiness = 0
        else:
            readiness = (train_val / match_val) * 100
            readiness = min(readiness, 200)

        with cols[i]:
            st.metric(
                label=metric,
                value=f"{readiness:.0f}%",
                delta=f"{train_val:.0f}/{match_val if pd.notna(match_val) else 0:.0f}"
            )

# === 7. If no valid players found ===
if valid_players == 0:
    st.warning("No players have a match followed by training sessions.")
