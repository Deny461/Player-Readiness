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
    col1, col2, col3 = st.columns([0.08, 0.001, 0.72])
    with col1:
        st.image("BostonBoltsLogo.png", width=120)
    with col2:
        st.markdown(
            "<div style='border-left:2px solid gray; height:90px;'></div>",
            unsafe_allow_html=True
        )
    with col3:
        st.image("MLSNextLogo.png", width=120)

# === TITLE ===
with st.container():
    st.markdown(
        "<h1 style='text-align:center;font-size:72px;margin-top:-60px;'>Player Readiness</h1>",
        unsafe_allow_html=True
    )

# === SESSION-STATE INIT ===
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "proceed" not in st.session_state:
    st.session_state.proceed = False
if "show_debug" not in st.session_state:
    st.session_state.show_debug = False

# === LANDING PAGE ===
if st.session_state.page == "Home":
    st.markdown("### Select a Dashboard")
    choice = st.selectbox(
        "Choose which dashboard you want to view:",
        ["Player Gauges Dashboard", "ACWR Dashboard"]
    )
    if st.button("Continue", key="dashboard_continue"):
        st.session_state.page = choice
        st.session_state.proceed = False
        st.rerun()
    st.stop()

# === PLAYER GAUGES DASHBOARD ===
if st.session_state.page == "Player Gauges Dashboard":
    # --- Debug toggle ---
    btn_label = "Hide Debug Info" if st.session_state.show_debug else "Show Debug Info"
    if st.button(btn_label, key="debug_toggle"):
        st.session_state.show_debug = not st.session_state.show_debug
        st.rerun()

    st.markdown("## Player Gauges Dashboard")

    # --- Step 1: select team ---
    if not st.session_state.proceed:
        teams = [
            "U15 MLS Next","U16 MLS Next","U17 MLS Next","U19 MLS Next",
            "U15 MLS Next 2","U16 MLS Next 2","U17 MLS Next 2","U19 MLS Next 2"
        ]
        selected = st.selectbox("Select Team", teams, key="team_select")
        if st.button("Continue", key="team_continue"):
            st.session_state.proceed = True
            st.session_state.selected_team = selected
            st.rerun()
        st.stop()

    # --- Step 2: back to landing ---
    if st.button("Select Dashboard", key="gauges_back"):
        st.session_state.page = "Home"
        st.session_state.proceed = False
        st.rerun()

    # === CSV Loader ===
    @st.cache_data
    def load_data(path):
        df = pd.read_csv(path)
        df['Date'] = pd.to_datetime(df['Start Date'], format='%m/%d/%y', errors='coerce')
        if df['Date'].isna().all():
            df['Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        return df

    # === Gauge Helpers ===
    def get_color(ratio):
        if ratio < 0.5: return "red"
        if ratio < 0.75: return "orange"
        if ratio < 1.0: return "yellow"
        if ratio <= 1.30: return "green"
        return "black"

    def create_readiness_gauge(value, benchmark, label):
        ratio = 0 if pd.isna(benchmark) or benchmark == 0 else value/benchmark
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=round(ratio,2),
            number={"font":{"size":20}},
            gauge={
                "axis": {"range":[0, max(1.5,ratio)], "showticklabels":False},
                "bar": {"color": get_color(ratio)},
                "steps": [
                    {"range":[0,0.5], "color":"#ffcccc"},
                    {"range":[0.5,0.75], "color":"#ffe0b3"},
                    {"range":[0.75,1.0], "color":"#ffffcc"},
                    {"range":[1.0,1.3], "color":"#ccffcc"},
                    {"range":[1.3, max(1.5,ratio)], "color":"#e6e6e6"}
                ]
            }
        ))
        fig.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=180)
        return fig

    # === Load & Prep Data ===
    team = st.session_state.selected_team
    path = f"Player Data/{team}_PD_Data.csv"
    if not os.path.exists(path):
        st.error(f"File not found: {path}")
        st.stop()
    df = load_data(path)
    df = df.dropna(subset=["Date","Session Type","Athlete Name","Segment Name"])
    df = df[df["Segment Name"]=="Whole Session"].sort_values("Date")

    # --- Anchors ---
    match_df = df[df["Session Type"]=="Match Session"]
    if match_df.empty:
        st.markdown("**Latest Match Date Used:** _None found_")
        st.stop()
    latest_match_date = match_df["Date"].max()
    st.markdown(f"**Latest Match Date Used:** `{latest_match_date.date()}`")

    training_df = df[df["Session Type"]=="Training Session"]
    if training_df.empty:
        st.warning("No training sessions found.")
        st.stop()
    latest_training_date = training_df["Date"].max()
    iso_year, iso_week, _ = latest_training_date.isocalendar()
    st.markdown(f"🌐 Global Latest Training Date: {latest_training_date.date()}")

    # --- Metrics Setup ---
    metrics = [
        "Distance (m)",
        "High Intensity Running (m)",
        "Sprint Distance (m)",
        "No. of Sprints",
        "Top Speed (kph)"
    ]
    metric_labels = {
        "Distance (m)": "Total Distance",
        "High Intensity Running (m)": "HSR",
        "Sprint Distance (m)": "Sprint Distance",
        "No. of Sprints": "# of Sprints",
        "Top Speed (kph)": "Top Speed"
    }

    # === Loop Players ===
    for player in sorted(df["Athlete Name"].dropna().unique()):
        p_df = df[df["Athlete Name"]==player].copy()
        p_df["Duration (mins)"] = pd.to_numeric(p_df["Duration (mins)"], errors="coerce")
        for m in metrics:
            p_df[m] = pd.to_numeric(p_df[m], errors="coerce")

        # Matches <= latest_match_date
        matches = p_df[
            (p_df["Session Type"]=="Match Session") &
            (p_df["Date"]<=latest_match_date) &
            (p_df["Duration (mins)"]>0)
        ].sort_values("Date")
        if matches.empty:
            continue

        # Training this week
        iso = p_df["Date"].dt.isocalendar()
        training_week = p_df[
            (p_df["Session Type"]=="Training Session") &
            (iso["week"]==iso_week) &
            (iso["year"]==iso_year)
        ]
        if training_week.empty:
            training_week = pd.DataFrame([{
                "Athlete Name":player,
                "Date": latest_training_date,
                "Session Type":"Training Session",
                "Segment Name":"Whole Session",
                "Distance (m)":0,
                "High Intensity Running (m)":0,
                "Sprint Distance (m)":0,
                "No. of Sprints":0,
                "Top Speed (kph)":0,
                "Duration (mins)":0
            }])

        # Previous non-zero week totals
        prev = p_df[
            (p_df["Session Type"]=="Training Session") &
            (p_df["Date"]<training_week["Date"].min())
        ]
        if not prev.empty:
            prev["Year"] = prev["Date"].dt.isocalendar().year
            prev["Week"] = prev["Date"].dt.isocalendar().week
            week_sums = prev.groupby(["Year","Week"])[metrics].sum().reset_index()
            valid = week_sums[(week_sums.drop(columns=["Year","Week"])>0).any(axis=1)]
            if not valid.empty:
                last = valid.iloc[-1]
                prev_week_str = f"Week {int(last['Week'])}, {int(last['Year'])}"
                prev_data = prev[
                    (prev["Date"].dt.isocalendar().week==last["Week"]) &
                    (prev["Date"].dt.isocalendar().year==last["Year"])
                ]
                previous_week_total_map = {
                    m: prev_data[m].sum() for m in metrics if m!="Top Speed (kph)"
                }
            else:
                prev_week_str="None"
                previous_week_total_map={m:0 for m in metrics if m!="Top Speed (kph)"}
        else:
            prev_week_str="None"
            previous_week_total_map={m:0 for m in metrics if m!="Top Speed (kph)"}

        # Match per-90 benchmarks
        match_avg = {}
        for m in metrics:
            if m!="Top Speed (kph)":
                matches["Per90"] = matches[m]/matches["Duration (mins)"]*90
                match_avg[m] = matches["Per90"].mean()

        top_speed_benchmark = p_df["Top Speed (kph)"].max()
        grouped = training_week.agg({
            "Distance (m)":"sum",
            "High Intensity Running (m)":"sum",
            "Sprint Distance (m)":"sum",
            "No. of Sprints":"sum",
            "Top Speed (kph)":"max"
        }).to_frame().T

        st.markdown(f"### {player}")
        cols = st.columns(len(metrics))

        for i, metric in enumerate(metrics):
            # === Top Speed special case ===
            if metric=="Top Speed (kph)":
                train_val = grouped[metric].max()
                benchmark = top_speed_benchmark
                ratio = 0 if pd.isna(benchmark) or benchmark==0 else train_val/benchmark

                # Custom gauge up to 100% with four bands
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=round(ratio,2),
                    number={"font":{"size":20}},
                    gauge={
                        "axis":{"range":[0,1.0],"showticklabels":False},
                        "bar":{"color":
                            "red"    if ratio<0.5 else
                            "orange" if ratio<0.75 else
                            "yellow" if ratio<0.9 else
                            "green"
                        },
                        "steps":[
                            {"range":[0,0.5],"color":"#ffcccc"},
                            {"range":[0.5,0.75],"color":"#ffe0b3"},
                            {"range":[0.75,0.9],"color":"#ffffcc"},
                            {"range":[0.9,1.0],"color":"#ccffcc"},
                        ]
                    }
                ))
                fig.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=180)

                with cols[i]:
                    st.markdown(
                        f"<div style='text-align:center;font-weight:bold;'>{metric_labels[metric]}</div>",
                        unsafe_allow_html=True
                    )
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        key=f"{player}-top-{i}"
                    )
                    if ratio < 0.9:
                        st.markdown(
                            "<div style='text-align:center;color:red;font-weight:bold;'>"
                            "⚠️ Did not reach 90% of max speed this week"
                            "</div>",
                            unsafe_allow_html=True
                        )
                continue

            # === All other metrics ===
            train_val = grouped[metric].sum()
            benchmark = match_avg.get(metric, None)
            fig = create_readiness_gauge(train_val, benchmark, metric_labels[metric])

            with cols[i]:
                st.markdown(
                    f"<div style='text-align:center;font-weight:bold;'>{metric_labels[metric]}</div>",
                    unsafe_allow_html=True
                )
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key=f"{player}-{metric}-{i}"
                )

                # Projection & flag logic
                practices_done = training_week.shape[0]
                current_sum = training_week[metric].sum()
                previous_week_total = previous_week_total_map.get(metric, 0)

                iso_all = p_df["Date"].dt.isocalendar()
                p_df["PracticeNumber"] = (
                    p_df[p_df["Session Type"]=="Training Session"]
                    .groupby([iso_all.year, iso_all.week])
                    .cumcount()+1
                ).clip(upper=3)
                practice_avgs = (
                    p_df[p_df["Session Type"]=="Training Session"]
                    .groupby("PracticeNumber")[metric].mean()
                    .reindex([1,2,3], fill_value=0)
                )

                if previous_week_total>0 and current_sum>1.10*previous_week_total:
                    flag="⚠️"
                    flag_val=current_sum
                    projection_used=False
                    projected_total=None
                else:
                    if practices_done<3:
                        needed = list(range(practices_done+1,4))
                        projected_total = current_sum + practice_avgs.loc[needed].sum()
                        flag_val=projected_total
                        projection_used=True
                    else:
                        projected_total=None
                        flag_val=current_sum
                        projection_used=False

                    if previous_week_total>0 and flag_val>1.10*previous_week_total:
                        flag="🔮⚠️" if projection_used else "⚠️"
                    else:
                        flag=""

                # Flag message
                if flag:
                    if projection_used:
                        st.markdown(
                            "<div style='text-align:center;font-weight:bold;'>"
                            f"⚠️Projected total of {metric_labels[metric]} is on track to be > 110% of last week’s total"
                            "</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            "<div style='text-align:center;font-weight:bold;'>"
                            f"⚠️{metric_labels[metric]} is > 110% than last week’s total"
                            "</div>",
                            unsafe_allow_html=True
                        )

                # Debug info
                if st.session_state.show_debug:
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
        teams = [
            "U15 MLS Next","U16 MLS Next","U17 MLS Next","U19 MLS Next",
            "U15 MLS Next 2","U16 MLS Next 2","U17 MLS Next 2","U19 MLS Next 2"
        ]
        sel = st.selectbox("Select Team", teams, key="team_select_acwr")
        if st.button("Continue", key="acwr_continue"):
            st.session_state.proceed = True
            st.session_state.selected_team = sel
            st.rerun()
        st.stop()
    if st.button("Select Dashboard", key="acwr_back"):
        st.session_state.page = "Home"
        st.session_state.proceed = False
        st.rerun()
    st.info("This ACWR dashboard is under development 🚧")