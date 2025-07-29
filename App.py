# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(
    page_title="Player Dashboard",
    page_icon="BostonBoltsLogo.png",
    layout="wide"
)

# === LOGO HEADER ===
with st.container():
    col1, col2, col3 = st.columns([0.05,0.002,0.52])
    with col1: st.image("BostonBoltsLogo.png", width=220)
    with col2: st.markdown("<div style='border-left:2px solid gray;height:180px;'></div>", unsafe_allow_html=True)
    with col3: st.image("MLSNextLogo.png", width=220)

# === PAGE SELECTION ===
if "mode" not in st.session_state: st.session_state.mode = None
if "proceed" not in st.session_state: st.session_state.proceed = False

if not st.session_state.proceed:
    mode = st.selectbox("Choose Dashboard:", ["Player Readiness", "ACWR"])
    if st.button("Continue"):
        st.session_state.mode = mode
        st.session_state.proceed = True
        st.rerun()
    st.stop()

mode = st.session_state.mode
available_teams = ["U15 MLS Next","U16 MLS Next","U17 MLS Next","U19 MLS Next",
                   "U15 MLS Next 2","U16 MLS Next 2","U17 MLS Next 2","U19 MLS Next 2"]
selected_team = st.selectbox("Select Team", available_teams)

col_spacer, colA, colB, col_spacer2 = st.columns([0.0001,0.1,1.5,1])
with colA:
    if st.button("Back"):
        st.session_state.proceed = False
        st.rerun()

# === CSV Loader ===
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df['Date'] = pd.to_datetime(df['Start Date'], format='%m/%d/%y', errors='coerce')
    if df['Date'].isna().all():
        df['Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    return df

# === Load Data ===
filename = f"Player Data/{selected_team}_PD_Data.csv"
if not os.path.exists(filename): 
    st.error(f"File {filename} not found.")
    st.stop()

df = load_data(filename)
df = df.dropna(subset=["Date","Session Type","Athlete Name","Segment Name"])
df = df[df["Segment Name"]=="Whole Session"].sort_values("Date")

# === Anchors ===
match_df = df[df["Session Type"]=="Match Session"]
if match_df.empty: st.warning("No matches found"); st.stop()
latest_match_date = match_df["Date"].max()

training_df = df[df["Session Type"]=="Training Session"]
if training_df.empty: st.warning("No training sessions found"); st.stop()
latest_training_date = training_df["Date"].max()
iso_year, iso_week, _ = latest_training_date.isocalendar()

st.markdown(f"**Latest Match Date:** {latest_match_date.date()}")
st.markdown(f"🌐 Latest Training Date: {latest_training_date.date()}")

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

# === Gauge Helper ===
def get_color(ratio):
    if ratio < 0.5: return "red"
    elif ratio < 0.75: return "orange"
    elif ratio < 1.0: return "yellow"
    elif ratio <= 1.30: return "green"
    else: return "black"

def create_readiness_gauge(value, benchmark, label):
    ratio = 0 if pd.isna(benchmark) or benchmark==0 else value/benchmark
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

# === PAGE: PLAYER READINESS ===
if mode == "Player Readiness":
    players = sorted(df["Athlete Name"].dropna().unique())
    for player in players:
        player_data = df[df["Athlete Name"]==player].copy()
        player_data["Duration (mins)"] = pd.to_numeric(player_data["Duration (mins)"], errors="coerce")
        for m in metrics: player_data[m] = pd.to_numeric(player_data[m], errors="coerce")

        matches = player_data[(player_data["Session Type"]=="Match Session") &
                              (player_data["Date"]<=latest_match_date) &
                              (player_data["Duration (mins)"]>0)]
        if matches.empty: continue

        iso_vals = player_data["Date"].dt.isocalendar()
        training_week = player_data[(player_data["Session Type"]=="Training Session") &
                                    (iso_vals["week"]==iso_week) &
                                    (iso_vals["year"]==iso_year)]
        if training_week.empty:
            training_week = pd.DataFrame([{
                "Athlete Name":player,"Date":latest_training_date,
                "Session Type":"Training Session","Segment Name":"Whole Session",
                "Distance (m)":0,"High Intensity Running (m)":0,
                "Sprint Distance (m)":0,"No. of Sprints":0,"Top Speed (kph)":0,
                "Duration (mins)":0
            }])

        prev_training = player_data[(player_data["Session Type"]=="Training Session") &
                                    (player_data["Date"]<training_week["Date"].min())]
        previous_week_total_map = {m:0 for m in metrics if m!="Top Speed (kph)"}
        prev_week_str="None"
        if not prev_training.empty:
            prev_training['Year'] = prev_training['Date'].dt.isocalendar().year
            prev_training['Week'] = prev_training['Date'].dt.isocalendar().week
            week_sums = prev_training.groupby(['Year','Week'])[metrics].sum().reset_index()
            valid_weeks = week_sums[(week_sums.drop(columns=['Year','Week'])>0).any(axis=1)]
            if not valid_weeks.empty:
                last_valid = valid_weeks.iloc[-1]
                prev_week_str = f"Week {int(last_valid['Week'])}, {int(last_valid['Year'])}"
                previous_week_data = prev_training[
                    (prev_training['Date'].dt.isocalendar().week==last_valid['Week']) &
                    (prev_training['Date'].dt.isocalendar().year==last_valid['Year'])
                ]
                previous_week_total_map = {
                    m: previous_week_data[m].sum() for m in metrics if m!="Top Speed (kph)"
                }

        match_avg={}
        for m in metrics:
            if m!="Top Speed (kph)":
                matches["Per90"]=matches[m]/matches["Duration (mins)"]*90
                match_avg[m]=matches["Per90"].mean()

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
                st.markdown(f"<div style='text-align:center;font-weight:bold;'>{metric_labels[metric]}</div>", unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, key=f"{player}-{metric}")

                if metric!="Top Speed (kph)":
                    practices_done=training_week.shape[0]
                    current_sum=training_week[metric].sum()
                    previous_week_total=previous_week_total_map.get(metric,0)

                    iso_vals_all=player_data["Date"].dt.isocalendar()
                    player_data["PracticeNumber"]=(
                        player_data[player_data["Session Type"]=="Training Session"]
                        .groupby([iso_vals_all.year,iso_vals_all.week])
                        .cumcount()+1
                    ).clip(upper=3)
                    practice_avgs=(
                        player_data[player_data["Session Type"]=="Training Session"]
                        .groupby("PracticeNumber")[metric].mean()
                        .reindex([1,2,3],fill_value=0)
                    )

                    if previous_week_total>0 and current_sum>1.10*previous_week_total:
                        flag="⚠️"; flag_val=current_sum; projection_used=False; projected_total="N/A"
                    else:
                        if practices_done<3:
                            needed_practices=[p for p in range(practices_done+1,4)]
                            projected_total=current_sum+practice_avgs.loc[needed_practices].sum()
                            flag_val=projected_total; projection_used=True
                        else:
                            projected_total="N/A"; flag_val=current_sum; projection_used=False
                        if previous_week_total>0 and flag_val>1.10*previous_week_total:
                            flag="🔮⚠️" if projection_used else "⚠️"
                        else: flag=""

                    iso_all=player_data["Date"].dt.isocalendar()
                    weekly=(player_data[player_data["Session Type"]=="Training Session"]
                            .groupby([iso_all.year,iso_all.week])[metric].sum().reset_index())
                    weekly.columns=["Year","Week","Load"]
                    weekly["Chronic"]=weekly["Load"].rolling(4,min_periods=1).mean()
                    weekly["ACWR"]=weekly["Load"]/weekly["Chronic"]
                    latest_acwr=weekly["ACWR"].iloc[-1] if not weekly.empty else 0
                    if latest_acwr<0.8: acwr_flag="⚠️ Undertrained"
                    elif latest_acwr>1.3: acwr_flag="⚠️ Overtrained"
                    else: acwr_flag="✅ Optimal"

                    st.markdown(f"""
                    <div style='font-size:14px;color:#555;'>
                        <b>Debug for {metric_labels[metric]}</b><br>
                        • Previous Week Used: {prev_week_str}<br>
                        • Previous Week Total: {previous_week_total:.1f}<br>
                        • Current Week So Far: {current_sum:.1f}<br>
                        • Practices Done: {practices_done}<br>
                        • Historical Practice Avgs: {practice_avgs.to_dict()}<br>
                        • Projected Total: {projected_total if projection_used else 'N/A'}<br>
                        • Final Used: {flag_val:.1f} ({'Projected' if projection_used else 'Actual'})<br>
                        • Threshold (110%): {1.10*previous_week_total:.1f}<br>
                        • ⚠️ Load Flag: {'YES' if flag else 'NO'} {flag}<br>
                        • ACWR: {latest_acwr:.2f} → {acwr_flag}
                    </div>
                    """, unsafe_allow_html=True)

# === PAGE: ACWR ===
if mode == "ACWR":
    st.markdown("## ACWR Trends")
    players = sorted(df["Athlete Name"].dropna().unique())
    for player in players:
        player_data = df[df["Athlete Name"]==player]
        iso_all = player_data["Date"].dt.isocalendar()
        weekly = player_data[player_data["Session Type"]=="Training Session"].groupby(
            [iso_all.year, iso_all.week]
        )[metrics].sum().reset_index()
        weekly["Chronic"] = weekly[metrics].rolling(4,min_periods=1).mean()
        for m in metrics:
            if m=="Top Speed (kph)": continue
            weekly[f"ACWR_{m}"] = weekly[m] / weekly["Chronic"][m]

        fig = go.Figure()
        for m in metrics:
            if m=="Top Speed (kph)": continue
            fig.add_trace(go.Scatter(x=weekly.index, y=weekly[f"ACWR_{m}"], mode="lines+markers", name=metric_labels[m]))
        fig.add_hrect(y0=0.8, y1=1.3, fillcolor="green", opacity=0.1, line_width=0)
        fig.add_hrect(y0=0, y1=0.8, fillcolor="red", opacity=0.05, line_width=0)
        fig.add_hrect(y0=1.3, y1=3, fillcolor="orange", opacity=0.05, line_width=0)
        fig.update_layout(title=f"ACWR Trends for {player}", yaxis_title="ACWR", height=400)
        st.plotly_chart(fig, use_container_width=True)
