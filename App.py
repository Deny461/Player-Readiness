import streamlit as st
import pandas as pd

# === CONFIG ===
selected_team = "U15 MLS Next"  # Change if needed
metric = "Sprint Distance (m)"  # You can swap to any metric
player = "Andy Zecena"       # Set this to a real player name from your dataset

# === Load and clean your CSV ===
filename = f"Player Data/{selected_team}_PD_Data.csv"
df = pd.read_csv(filename)
df["Date"] = pd.to_datetime(df["Start Date"], errors="coerce")
df = df[df["Segment Name"] == "Whole Session"]
df["Duration (mins)"] = pd.to_numeric(df["Duration (mins)"], errors="coerce")
df[metric] = pd.to_numeric(df[metric], errors="coerce")

# === Filter to player ===
player_data = df[df["Athlete Name"] == player].copy()
player_data = player_data.dropna(subset=["Date", metric, "Duration (mins)"])

# === Match sessions ===
matches = player_data[player_data["Session Type"] == "Match Session"].sort_values("Date")
if matches.empty:
    st.error("❌ No match data found.")
    st.stop()

latest_match = matches.iloc[-1]
match_cutoff_date = latest_match["Date"]
match_games = matches[matches["Date"] <= match_cutoff_date]
match_games = match_games[match_games["Duration (mins)"] > 0]

# === Match average per 90 ===
match_games["Per90"] = match_games[metric] / match_games["Duration (mins)"] * 90
match_avg = match_games["Per90"].mean()

# === 3 training sessions after the last match ===
trainings = player_data[
    (player_data["Session Type"] == "Training Session") &
    (player_data["Date"] > match_cutoff_date)
].sort_values("Date").head(3)

training_sum = trainings[metric].sum()
ratio = training_sum / match_avg if match_avg else 0

# === DISPLAY ===
st.header(f"🧠 Debug: {player} – {metric}")
st.subheader("1. Match Sessions Used")
st.dataframe(match_games[["Date", "Duration (mins)", metric, "Per90"]])
st.write(f"📊 **Match Avg per 90:** `{match_avg:.2f}`")

st.subheader("2. Training Sessions Used")
st.dataframe(trainings[["Date", metric]])
st.write(f"📈 **Training Total (3 sessions):** `{training_sum:.2f}`")

st.subheader("3. Final Ratio")
st.write(f"✅ **Ratio =** `{training_sum:.2f} / {match_avg:.2f} = {ratio:.2f}`")
