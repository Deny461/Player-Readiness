# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

st.set_page_config(
    page_title="Performance Dashboard",
    page_icon="BostonBoltsLogo.png",
    layout="wide"
)

# === LOGO HEADER ===
with st.container():
    col1, col2, col3 = st.columns([0.05, 0.002, 0.52])
    with col1: 
        st.image("BostonBoltsLogo.png", width=220)
    with col2: 
        st.markdown("<div style='border-left:2px solid gray; height:180px;'></div>", unsafe_allow_html=True)
    with col3: 
        st.image("MLSNextLogo.png", width=220)

# === TITLE ===
with st.container():
    st.markdown("<h1 style='text-align:center;font-size:72px;margin-top:-60px;'>Performance Dashboard</h1>", unsafe_allow_html=True)

# === CSV Loader ===
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df['Date'] = pd.to_datetime(df['Start Date'], format='%m/%d/%y', errors='coerce')
    if df['Date'].isna().all():
        df['Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    return df

# === Session Control ===
if "page" not in st.session_state:
    st.session_state.page = "Home"

page_choice = st.selectbox("Choose Page", ["Player Readiness", "ACWR"])

available_teams = ["U15 MLS Next","U16 MLS Next","U17 MLS Next","U19 MLS Next",
                   "U15 MLS Next 2","U16 MLS Next 2","U17 MLS Next 2","U19 MLS Next 2"]
selected_team = st.selectbox("Select Team", available_teams)

filename = f"Player Data/{selected_team}_PD_Data.csv"
if not os.path.exists(filename):
    st.error(f"File {filename} not found.")
    st.stop()

df = load_data(filename)
df = df.dropna(subset=["Date","Session Type","Athlete Name","Segment Name"])
df = df[df["Segment Name"]=="Whole Session"].sort_values("Date")

# === Metrics ===
metrics = ["Distance (m)","High Intensity Running (m)","Sprint Distance (m)",
           "No. of Sprints","Top Speed (kph)"]
metric_labels = {
    "Distance (m)":"Total Distance",
    "High Intensity Running (m)":"HSR",
    "Sprint Distance (m)":"Sprint Distance",
    "No. of Sprints":"# of Sprints",
    "Top Speed (kph)":"Top Speed"
}

# === Gauge Function ===
def get_color(ratio):
    if ratio < 0.5: return "red"
    elif ratio < 0.75: return "orange"
    elif ratio < 1.0: return "yellow"
    elif ratio <= 1.30: return "green"
    else: return "black"

def create_readiness_gauge(value, benchmark, label):
    ratio = 0 if pd.isna(benchmark) or benchmark == 0 else value/benchmark
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(ratio,2),
        number={"font":{"size":20}},
        gauge={
            "axis":{"range":[0,max(1.5,ratio)],"showticklabels":False},
            "bar":{"color":get_color(ratio)},
            "steps":[
                {"range":[0,0.5],"color":"#ffcccc"},
                {"range":[0.5,0.75],"color":"#ffe0b3"},
                {"range":[0.75,1.0],"color":"#ffffcc"},
                {"range":[1.0,1.3],"color":"#ccffcc"},
                {"range":[1.3,max(1.5,ratio)],"color":"#e6e6e6"}]
        }
    ))
    fig.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=180)
    return fig

# === Player Readiness Page ===
if page_choice == "Player Readiness":
    match_df = df[df["Session Type"]=="Match Session"]
    if match_df.empty: 
        st.markdown("**Latest Match Date Used:** _None found_")
        st.stop()

    latest_match_date = match_df["Date"].max()
    st.markdown(f"**Latest Match Date Used:** `{latest_match_date.date()}`")

    training_df = df[df["Session Type"]=="Training Session"]
    if training_df.empty:
        st.warning("No training sessions found in dataset.")
        st.stop()

    latest_training_date = training_df["Date"].max()
    iso_year, iso_week, _ = latest_training_date.isocalendar()
    st.markdown(f"🌐 Global Latest Training Date: {latest_training_date.date()}")

    players = sorted(df["Athlete Name"].dropna().unique())
    for player in players:
        player_data = df[df["Athlete Name"]==player].copy()
        player_data["Duration (mins)"] = pd.to_numeric(player_data["Duration (mins)"], errors="coerce")
        for m in metrics: 
            player_data[m] = pd.to_numeric(player_data[m], errors="coerce")

        matches = player_data[(player_data["Session Type"]=="Match Session") &
                              (player_data["Date"]<=latest_match_date) &
                              (player_data["Duration (mins)"]>0)].sort_values("Date")
        if matches.empty: continue

        iso_vals = player_data["Date"].dt.isocalendar()
        training_week = player_data[(player_data["Session Type"]=="Training Session") &
                                    (iso_vals["week"]==iso_week) &
                                    (iso_vals["year"]==iso_year)]
        if training_week.empty:
            training_week = pd.DataFrame([{
                "Athlete Name":player,"Date":latest_training_date,"Session Type":"Training Session",
                "Segment Name":"Whole Session","Distance (m)":0,"High Intensity Running (m)":0,
                "Sprint Distance (m)":0,"No. of Sprints":0,"Top Speed (kph)":0,"Duration (mins)":0
            }])

        match_avg = {}
        for m in metrics:
            if m!="Top Speed (kph)":
                matches["Per90"] = matches[m]/matches["Duration (mins)"]*90
                match_avg[m] = matches["Per90"].mean()

        top_speed_benchmark = player_data["Top Speed (kph)"].max()
        grouped_trainings = training_week.agg({
            "Distance (m)":"sum","High Intensity Running (m)":"sum",
            "Sprint Distance (m)":"sum","No. of Sprints":"sum","Top Speed (kph)":"max"
        }).to_frame().T

        st.markdown(f"### {player}")
        cols = st.columns(len(metrics))
        for i,metric in enumerate(metrics):
            if metric=="Top Speed (kph)":
                train_val=grouped_trainings[metric].max()
                benchmark=top_speed_benchmark
            else:
                train_val=grouped_trainings[metric].sum()
                benchmark=match_avg.get(metric,None)

            fig=create_readiness_gauge(train_val,benchmark,metric_labels[metric])
            with cols[i]:
                st.markdown(f"<div style='text-align:center;font-weight:bold;'>{metric_labels[metric]}</div>",unsafe_allow_html=True)
                st.plotly_chart(fig,use_container_width=True,key=f"{player}-{metric}")

# === ACWR Page ===
if page_choice == "ACWR":
    st.subheader("ACWR Dashboard")
    players = sorted(df["Athlete Name"].dropna().unique())
    for player in players:
        player_data = df[df["Athlete Name"]==player].copy()
        player_data["Date"] = pd.to_datetime(player_data["Date"])
        player_data = player_data.sort_values("Date")
        for m in metrics: 
            player_data[m] = pd.to_numeric(player_data[m], errors="coerce")

        # ACWR calc: acute = last 7 days, chronic = last 28 days
        acwr_data = []
        for date in player_data["Date"].unique():
            acute_window = player_data[(player_data["Date"]<=date) & (player_data["Date"]>date-pd.Timedelta(days=7))]
            chronic_window = player_data[(player_data["Date"]<=date) & (player_data["Date"]>date-pd.Timedelta(days=28))]
            ratios = {}
            for m in metrics:
                acute = acute_window[m].sum()
                chronic = chronic_window[m].sum()/4 if len(chronic_window)>0 else 0
                ratios[m] = acute/chronic if chronic>0 else 0
            acwr_data.append({"Date":date, **ratios})
        acwr_df = pd.DataFrame(acwr_data)

        # Line chart with zones
        fig = go.Figure()
        for m in metrics:
            fig.add_trace(go.Scatter(x=acwr_df["Date"], y=acwr_df[m], mode="lines+markers", name=metric_labels[m]))
        # Add zones
        fig.add_hrect(y0=0, y1=0.8, fillcolor="red", opacity=0.2, line_width=0, annotation_text="Undertrained", annotation_position="top left")
        fig.add_hrect(y0=0.8, y1=1.3, fillcolor="green", opacity=0.2, line_width=0, annotation_text="Optimal", annotation_position="top left")
        fig.add_hrect(y0=1.3, y1=3, fillcolor="orange", opacity=0.2, line_width=0, annotation_text="Overtrained", annotation_position="top left")

        fig.update_layout(title=f"{player} - ACWR", yaxis_title="ACWR", xaxis_title="Date", height=400)
        st.plotly_chart(fig, use_container_width=True)
