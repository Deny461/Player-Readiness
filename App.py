# === 1. Imports and Setup ===
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

st.set_page_config(
    page_title="Player Readiness",
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
    st.markdown("<h1 style='text-align:center;font-size:72px;margin-top:-60px;'>Player Readiness</h1>", unsafe_allow_html=True)

# === SESSION CONTROL ===
if "page" not in st.session_state:
    st.session_state.page = "Home"

# === Session State Initialization ===
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "proceed" not in st.session_state:
    st.session_state.proceed = False

# === LANDING PAGE ===
if st.session_state.page == "Home":
    st.markdown("### Select a Dashboard")

    dashboard_choice = st.selectbox(
        "Choose which dashboard you want to view:",
        ["Player Gauges Dashboard", "ACWR Dashboard"]
    )

    if st.button("Continue", key="dashboard_continue"):
        st.session_state.page = dashboard_choice
        st.session_state.proceed = False  # reset team step
        st.rerun()

    st.stop()

# === PLAYER GAUGES DASHBOARD ===
if st.session_state.page == "Player Gauges Dashboard":
    st.markdown("## Player Gauges Dashboard")

    if not st.session_state.proceed:
        available_teams = ["U15 MLS Next","U16 MLS Next","U17 MLS Next","U19 MLS Next",
                           "U15 MLS Next 2","U16 MLS Next 2","U17 MLS Next 2","U19 MLS Next 2"]
        selected_team = st.selectbox("Select Team", available_teams, key="team_select")

        if st.button("Continue", key="team_continue"):
            st.session_state.proceed = True
            st.session_state.selected_team = selected_team
            st.rerun()
        st.stop()

    # Show Select Dashboard button
    if st.button("Select Dashboard", key="gauges_back"):
        st.session_state.page = "Home"
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

    # === Session Control ===
    if "proceed" not in st.session_state: 
        st.session_state.proceed = False
    available_teams = ["U15 MLS Next","U16 MLS Next","U17 MLS Next","U19 MLS Next",
                    "U15 MLS Next 2","U16 MLS Next 2","U17 MLS Next 2","U19 MLS Next 2"]
    selected_team = st.selectbox("Select Team", available_teams)

    # === Load Data ===
    filename = f"Player Data/{selected_team}_PD_Data.csv"
    if not os.path.exists(filename): 
        st.error(f"File {filename} not found.")
        st.stop()

    df = load_data(filename)
    df = df.dropna(subset=["Date","Session Type","Athlete Name","Segment Name"])
    df = df[df["Segment Name"]=="Whole Session"].sort_values("Date")

    # === Latest Match and Training Anchors ===
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

    # === Loop Players ===
    players = sorted(df["Athlete Name"].dropna().unique())
    for player in players:
        player_data = df[df["Athlete Name"]==player].copy()
        player_data["Duration (mins)"] = pd.to_numeric(player_data["Duration (mins)"], errors="coerce")
        for m in metrics: 
            player_data[m] = pd.to_numeric(player_data[m], errors="coerce")

        # Matches before latest training
        matches = player_data[(player_data["Session Type"]=="Match Session") &
                            (player_data["Date"]<=latest_match_date) &
                            (player_data["Duration (mins)"]>0)].sort_values("Date")
        if matches.empty: 
            continue

        # Training in global latest training week
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

        # Find most recent previous training week with data
        prev_training = player_data[(player_data["Session Type"]=="Training Session") &
                                    (player_data["Date"]<training_week["Date"].min())]
        # Find most recent previous training week with actual data (>0 load)
        prev_training = player_data[
            (player_data["Session Type"]=="Training Session") &
            (player_data["Date"]<training_week["Date"].min())
        ]

        if not prev_training.empty:
            # Group by ISO week/year to filter out 0-load weeks
            prev_training['Year'] = prev_training['Date'].dt.isocalendar().year
            prev_training['Week'] = prev_training['Date'].dt.isocalendar().week
            week_sums = prev_training.groupby(['Year','Week'])[metrics].sum().reset_index()

            # Only keep weeks with non-zero totals
            valid_weeks = week_sums[(week_sums.drop(columns=['Year','Week']) > 0).any(axis=1)]

            if not valid_weeks.empty:
                last_valid = valid_weeks.iloc[-1]  # most recent non-zero week
                prev_week_str = f"Week {int(last_valid['Week'])}, {int(last_valid['Year'])}"
                previous_week_data = prev_training[
                    (prev_training['Date'].dt.isocalendar().week == last_valid['Week']) &
                    (prev_training['Date'].dt.isocalendar().year == last_valid['Year'])
                ]
                previous_week_total_map = {
                    m: previous_week_data[m].sum() for m in metrics if m!="Top Speed (kph)"
                }
            else:
                prev_week_str="None"
                previous_week_total_map={m:0 for m in metrics if m!="Top Speed (kph)"}
        else:
            prev_week_str="None"
            previous_week_total_map={m:0 for m in metrics if m!="Top Speed (kph)"}

        # Match averages per90 (exclude Top Speed)
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

                if metric!="Top Speed (kph)":
                    practices_done=training_week.shape[0]
                    current_sum=training_week[metric].sum()
                    previous_week_total=previous_week_total_map.get(metric,0)

                    # Historical Averages
                    iso_vals_all=player_data["Date"].dt.isocalendar()
                    player_data["PracticeNumber"] = (
                        player_data[player_data["Session Type"]=="Training Session"]
                        .groupby([iso_vals_all.year, iso_vals_all.week])
                        .cumcount()+1
                    ).clip(upper=3)
                    practice_avgs = (
                        player_data[player_data["Session Type"]=="Training Session"]
                        .groupby("PracticeNumber")[metric].mean()
                        .reindex([1,2,3], fill_value=0)
                    )

                # Flagging logic
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
                    • ⚠️ Flag: {'YES' if flag else 'NO'}
                </div>
                """, unsafe_allow_html=True)

    
# === ACWR DASHBOARD ===
if st.session_state.page == "ACWR Dashboard":
    st.markdown("## ACWR Dashboard")

    if not st.session_state.proceed:
        available_teams = ["U15 MLS Next","U16 MLS Next","U17 MLS Next","U19 MLS Next",
                           "U15 MLS Next 2","U16 MLS Next 2","U17 MLS Next 2","U19 MLS Next 2"]
        selected_team = st.selectbox("Select Team", available_teams, key="team_select_acwr")

        if st.button("Continue", key="acwr_continue"):
            st.session_state.proceed = True
            st.session_state.selected_team = selected_team
            st.rerun()
        st.stop()

    if st.button("⬅ Select Dashboard", key="acwr_back"):
        st.session_state.page = "Home"
        st.session_state.proceed = False
        st.rerun()

    st.info("This ACWR dashboard is under development 🚧")