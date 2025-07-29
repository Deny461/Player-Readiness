# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

st.set_page_config(
    page_title="Boston Bolts Player Dashboard",
    page_icon="BostonBoltsLogo.png",
    layout="wide"
)

# === LOGO HEADER ===
with st.container():
    col1, col2, col3 = st.columns([0.05,0.002,0.52])
    with col1: st.image("BostonBoltsLogo.png", width=220)
    with col2: st.markdown("<div style='border-left:2px solid gray; height:180px;'></div>", unsafe_allow_html=True)
    with col3: st.image("MLSNextLogo.png", width=220)

# === TITLE ===
with st.container():
    st.markdown("<h1 style='text-align:center;font-size:60px;margin-top:-40px;'>Boston Bolts Player Dashboard</h1>", unsafe_allow_html=True)

# === CSV Loader ===
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df['Date'] = pd.to_datetime(df['Start Date'], format='%m/%d/%y', errors='coerce')
    if df['Date'].isna().all():
        df['Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    return df

# === Session Control ===
if "page" not in st.session_state: st.session_state.page = None
if "proceed" not in st.session_state: st.session_state.proceed = False

page_choice = st.selectbox("Choose Dashboard", ["Player Readiness", "ACWR"])
available_teams = ["U15 MLS Next","U16 MLS Next","U17 MLS Next","U19 MLS Next",
                   "U15 MLS Next 2","U16 MLS Next 2","U17 MLS Next 2","U19 MLS Next 2"]
selected_team = st.selectbox("Select Team", available_teams)

col_spacer, colA, colB, col_spacer2 = st.columns([0.0001,0.1,1.5,1])
with colA:
    if st.button("Continue"):
        st.session_state.page = page_choice
        st.session_state.proceed = True
        st.rerun()
with colB:
    if st.button("Back"):
        st.session_state.proceed = False
        st.session_state.page = None
        st.rerun()
if not st.session_state.proceed: st.stop()

# === Load Data ===
filename = f"Player Data/{selected_team}_PD_Data.csv"
if not os.path.exists(filename):
    st.error(f"File {filename} not found.")
    st.stop()

df = load_data(filename)
df = df.dropna(subset=["Date","Session Type","Athlete Name","Segment Name"])
df = df[df["Segment Name"]=="Whole Session"].sort_values("Date")

# === Metrics ===
metrics = ["Distance (m)","High Intensity Running (m)","Sprint Distance (m)","No. of Sprints","Top Speed (kph)"]
metric_labels = {"Distance (m)":"Total Distance","High Intensity Running (m)":"HSR",
                 "Sprint Distance (m)":"Sprint Distance","No. of Sprints":"# of Sprints","Top Speed (kph)":"Top Speed"}

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

# === ACWR Helper ===
def calculate_weekly_acwr(player_df, metric, chronic_weeks=4):
    player_df = player_df.sort_values("Date")
    iso = player_df["Date"].dt.isocalendar()
    weekly = player_df.groupby([iso.year, iso.week])[metric].sum().reset_index()
    weekly.columns = ["Year","Week",metric]
    weekly["Acute"] = weekly[metric]
    weekly["Chronic"] = weekly[metric].rolling(chronic_weeks, min_periods=1).mean()
    weekly["ACWR"] = weekly["Acute"] / weekly["Chronic"]
    weekly["Label"] = weekly["Year"].astype(str) + "-W" + weekly["Week"].astype(str)
    return weekly

# === Player Readiness Page ===
if st.session_state.page == "Player Readiness":
    match_df = df[df["Session Type"]=="Match Session"]
    if match_df.empty:
        st.warning("No matches in dataset.")
        st.stop()
    latest_match_date = match_df["Date"].max()
    st.markdown(f"**Latest Match Date Used:** `{latest_match_date.date()}`")

    players = sorted(df["Athlete Name"].dropna().unique())
    for player in players:
        player_data = df[df["Athlete Name"]==player].copy()
        player_data["Duration (mins)"] = pd.to_numeric(player_data["Duration (mins)"], errors="coerce")
        for m in metrics: player_data[m] = pd.to_numeric(player_data[m], errors="coerce")

        matches = player_data[(player_data["Session Type"]=="Match Session") &
                              (player_data["Date"]<=latest_match_date) &
                              (player_data["Duration (mins)"]>0)]
        if matches.empty: continue

        match_avg={}
        for m in metrics:
            if m!="Top Speed (kph)":
                matches["Per90"]=matches[m]/matches["Duration (mins)"]*90
                match_avg[m]=matches["Per90"].mean()

        top_speed_benchmark = player_data["Top Speed (kph)"].max()
        training_week = player_data[player_data["Session Type"]=="Training Session"].tail(3)

        grouped_trainings = training_week.agg({
            "Distance (m)":"sum","High Intensity Running (m)":"sum",
            "Sprint Distance (m)":"sum","No. of Sprints":"sum","Top Speed (kph)":"max"
        }).to_frame().T

        st.markdown(f"### {player}")
        cols=st.columns(len(metrics))
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

                st.markdown(f"""
                <div style='font-size:14px;color:#555;'>
                    <b>Debug for {metric_labels[metric]}</b><br>
                    • Training Total: {train_val:.1f}<br>
                    • Match Benchmark: {benchmark if benchmark else 0:.1f}<br>
                </div>
                """, unsafe_allow_html=True)

# === ACWR Page ===
elif st.session_state.page == "ACWR":
    players = sorted(df["Athlete Name"].dropna().unique())
    for player in players:
        st.markdown(f"## {player}")
        fig = go.Figure()

        for metric in metrics:
            if metric=="Top Speed (kph)":
                continue
            weekly_acwr = calculate_weekly_acwr(df[df["Athlete Name"]==player], metric)
            fig.add_trace(go.Scatter(
                x=weekly_acwr["Label"], y=weekly_acwr["ACWR"],
                mode="lines+markers", name=metric_labels[metric]
            ))

            if not weekly_acwr.empty:
                latest_row = weekly_acwr.iloc[-1]
                zone = "Undertrained" if latest_row['ACWR']<0.8 else "Optimal" if latest_row['ACWR']<=1.3 else "Overtrained"
                flag = "⚠️" if zone!="Optimal" else ""
                st.markdown(f"""
                <div style='font-size:14px;color:#555;'>
                    <b>Debug for {metric_labels[metric]}</b><br>
                    • Latest Acute: {latest_row['Acute']:.1f}<br>
                    • Latest Chronic: {latest_row['Chronic']:.1f}<br>
                    • Latest ACWR: {latest_row['ACWR']:.2f}<br>
                    • Zone: {zone} {flag}
                </div>
                """, unsafe_allow_html=True)

        fig.add_hrect(y0=0, y1=0.8, fillcolor="red", opacity=0.2, line_width=0)
        fig.add_hrect(y0=0.8, y1=1.3, fillcolor="green", opacity=0.2, line_width=0)
        fig.add_hrect(y0=1.3, y1=2.0, fillcolor="orange", opacity=0.2, line_width=0)

        fig.update_layout(title="Weekly ACWR (All Metrics)",
                          yaxis_title="ACWR Ratio", xaxis_title="Week",
                          height=400)
        st.plotly_chart(fig, use_container_width=True)
