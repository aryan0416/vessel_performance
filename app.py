# pyrefly: ignore [missing-import]
# Trigger reload
import streamlit as st
# pyrefly: ignore [missing-import]
import folium
# pyrefly: ignore [missing-import]
from streamlit_folium import st_folium
import re
import pandas as pd
from parser import parse_noon_report, get_vessel_info
import importlib, calculator
importlib.reload(calculator)
from calculator import calculate_performance, get_summary, generate_narrative
from charts import (
    chart_lsfo_vs_warranted, chart_rob_drawdown,
    chart_speed_vs_cp, chart_mgo_rob,
    chart_time_utilisation, chart_lsfo_by_system,
    chart_beaufort, chart_wind_speed
)

# Page config
st.set_page_config(
    page_title="Vessel Performance Report",
    layout="wide"
)

# Header
st.title("Vessel Performance Report")
st.markdown("Welcome. Please upload your Noon Report and define the Charter Party terms to review the vessel's performance analysis.")

# Sidebar: File Upload + CP Inputs
with st.sidebar:
    st.header("Upload & Settings")

    uploaded_file = st.file_uploader("Upload Noon Report (.xlsx)", type=["xlsx"])

    st.divider()
    st.header("Charter Party Terms")

    vessel_name  = st.text_input("Vessel Name", value="M/V DE XI")
    voyage_from  = st.text_input("Voyage From", value="Singapore EOPL")
    voyage_to    = st.text_input("Voyage To",   value="Sungai Linggi")

    st.subheader("Warranted Speed")
    cp_speed = st.number_input("CP Speed (knots)", value=12.5, step=0.5)

    st.subheader("Warranted LSFO Consumption")
    cp_lsfo_steam = st.number_input("Steaming / Maneuvering (MT/day)", value=23.5, step=0.5)
    cp_lsfo_idle  = st.number_input("Idle / At Anchor (MT/day)",       value=5.5,  step=0.1)

    st.subheader("Opening ROB")
    opening_rob_lsfo = st.number_input("Opening LSFO ROB (MT)", value=970.68, step=1.0)
    opening_rob_mgo  = st.number_input("Opening MGO ROB (MT)",  value=242.98, step=1.0)

    generate = st.button("Generate Report", type="primary", use_container_width=True)

# Main Area
if not uploaded_file:
    st.info("Please upload a Noon Report Excel file from the sidebar to get started.")
    st.stop()

# Process on button click
if generate or "df_result" not in st.session_state:
    if uploaded_file:
        with st.spinner("Analyzing data..."):
            # Save uploaded file temporarily
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            df_raw = parse_noon_report(tmp_path)
            info   = get_vessel_info(tmp_path)
            os.unlink(tmp_path)

            cp = {
                "vessel_name":      vessel_name or info.get("vessel_name", "Unknown"),
                "voyage_from":      voyage_from,
                "voyage_to":        voyage_to,
                "cp_speed":         cp_speed,
                "cp_lsfo_steam":    cp_lsfo_steam,
                "cp_lsfo_idle":     cp_lsfo_idle,
                "opening_rob_lsfo": opening_rob_lsfo,
                "opening_rob_mgo":  opening_rob_mgo,
            }

            st.session_state.df_result = calculate_performance(df_raw, cp)
            st.session_state.summary   = get_summary(st.session_state.df_result, cp)

# Retrieve data from session state
df   = st.session_state.df_result
summ = st.session_state.summary

# Layout: Tabs for better User Experience
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Performance Overview", 
    "Daily Operations", 
    "Engine & Consumption", 
    "Contract Comparison",
    "Visual Analysis",
    "Voyage Map",
    "Route Optimizer"
])

# TAB 1 - REPORT SUMMARY
with tab1:
    st.header("Performance Overview")
    st.caption(f"{summ['voyage_from']} to {summ['voyage_to']} | {summ['period_start']} – {summ['period_end']}")
    st.write("A high-level view of the vessel's performance for this period.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Reporting Days",    summ["reporting_days"])
    col2.metric("Total Distance",    f"{summ['total_distance_nm']} nm")
    col3.metric("Avg Speed (Stmg)",  f"{summ['avg_speed']} Kts",
                delta=f"{round(summ['avg_speed'] - summ['cp_speed'], 2)} vs CP {summ['cp_speed']} Kts",
                delta_color="inverse")
    col4.metric("Idle Days",         summ["idle_days"])

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Total LSFO",        f"{summ['total_lsfo']} MT",
                delta=f"{summ['lsfo_diff']} vs Warranted {summ['warranted_lsfo']} MT",
                delta_color="inverse")
    col6.metric("Closing LSFO ROB",  f"{summ['closing_rob_lsfo']} MT")
    col7.metric("MGO Consumed",      f"{summ['total_mgo']} MT")
    col8.metric("Avg Daily LSFO",    f"{summ['avg_daily_lsfo']} MT/Day",
                delta=f"vs CP {summ['cp_daily_lsfo']} MT/Day",
                delta_color="inverse")

    st.divider()
    
    # Auto-generated narrative
    narrative = generate_narrative(df, summ)
    
    st.subheader("Voyage Narrative")
    for line in narrative.split("\n\n"):
        st.markdown(f"• {line}")

# TAB 2 - DAILY OPERATIONS LOG
with tab2:
    st.header("Daily Operations Log")
    st.write("A day-by-day breakdown of distance, speed, and weather conditions.")

    display_df = df[[
        "date", "latitude", "longitude", "operation",
        "engine_distance", "avg_speed", "cp_speed",
        "rpm", "slip_pct", "wind_speed", "beaufort", "remarks"
    ]].copy()

    # Clean up numbers — round decimals safely and handle Idle states
    display_df["engine_distance"] = display_df.apply(
        lambda r: "-" if r["operation"] == "Idle" else round(r["engine_distance"], 2), axis=1)
    
    display_df["avg_speed"]  = pd.to_numeric(display_df["avg_speed"], errors="coerce").round(2)
    display_df["cp_speed"]   = pd.to_numeric(display_df["cp_speed"], errors="coerce").round(2)
    
    display_df["rpm"]        = display_df["rpm"].apply(lambda x: int(x) if pd.notnull(x) and x > 0 else "-")
    display_df["slip_pct"]   = display_df["slip_pct"].apply(lambda x: round(x, 2) if pd.notnull(x) and x > 0 else "-")
    
    display_df["wind_speed"] = pd.to_numeric(display_df["wind_speed"], errors="coerce").round(1)
    display_df["beaufort"]   = display_df["beaufort"].apply(lambda x: int(x) if pd.notnull(x) else "-")

    display_df["date"] = display_df["date"].dt.strftime("%d-%b")
    display_df.columns = [
        "Date", "Latitude", "Longitude", "Operation",
        "Dist (nm)", "Avg Spd", "CP Spd",
        "RPM", "Slip %", "Wind Spd", "BF", "Remarks"
    ]

    def highlight_ops(row):
        if row["Operation"] == "Maneuvering":
            return ["background-color: #fff3cd; color: black"] * len(row)
        elif row["Operation"] == "Idle":
            return ["background-color: #f8f9fa; color: black"] * len(row)
        return [""] * len(row)

    st.dataframe(
        display_df.style.apply(highlight_ops, axis=1),
        use_container_width=True,
        hide_index=True
    )

# TAB 3 - ENGINE SUMMARY
with tab3:
    st.header("Engine Summary")
    st.write("Detailed fuel consumption tracking and computed Remaining On Board (ROB) values.")

    eng_df = df[[
        "date", "operation",
        "me_lsfo", "ae_lsfo", "boiler_lsfo", "total_lsfo",
        "warranted_lsfo", "lsfo_diff",
        "total_mgo", "computed_rob_lsfo", "computed_rob_mgo"
    ]].copy()

    eng_df["date"] = eng_df["date"].dt.strftime("%d-%b")
    eng_df.columns = [
        "Date", "Operation",
        "ME LSFO", "AE LSFO", "Boiler LSFO", "Total LSFO",
        "Warranted LSFO", "Difference",
        "Total MGO", "ROB LSFO", "ROB MGO"
    ]

    # Add totals row
    totals = pd.DataFrame([{
        "Date": "TOTAL", "Operation": "—",
        "ME LSFO":       round(df["me_lsfo"].sum(), 3),
        "AE LSFO":       round(df["ae_lsfo"].sum(), 3),
        "Boiler LSFO":   round(df["boiler_lsfo"].sum(), 3),
        "Total LSFO":    round(df["total_lsfo"].sum(), 3),
        "Warranted LSFO":round(df["warranted_lsfo"].sum(), 3),
        "Difference":    round(df["lsfo_diff"].sum(), 3),
        "Total MGO":     round(df["total_mgo"].sum(), 3),
        "ROB LSFO":      "—",
        "ROB MGO":       "—",
    }])
    eng_df = pd.concat([eng_df, totals], ignore_index=True)

    def highlight_diff(val):
        try:
            v = float(val)
            if v > 0:   return "color: red; font-weight: bold"
            if v < 0:   return "color: green"
        except:
            pass
        return ""

    st.dataframe(
        eng_df.style.map(highlight_diff, subset=["Difference"]),
        use_container_width=True,
        hide_index=True
    )

# TAB 4 - VOYAGE SUMMARY
with tab4:
    st.header("Contract Comparison")
    st.write("A side-by-side comparison of actual vessel performance against Charter Party terms.")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Leg Breakdown")
        legs = df[["date", "operation", "engine_distance", "avg_speed"]].copy()
        legs["date"] = legs["date"].dt.strftime("%d-%b")
        legs.columns = ["Date", "Operation", "Distance (nm)", "Avg Speed (kts)"]
        st.dataframe(legs, use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("CP Warranted vs Actual")
        comparison = pd.DataFrame([
            {"Parameter": "Speed (Steaming Avg)",   "CP Warranted": f"{summ['cp_speed']} Kts",        "Actual": f"{summ['avg_speed']} Kts"},
            {"Parameter": "Total LSFO Consumed",    "CP Warranted": f"{summ['warranted_lsfo']} MT",   "Actual": f"{summ['total_lsfo']} MT"},
            {"Parameter": "Avg Daily LSFO",         "CP Warranted": f"{summ['cp_daily_lsfo']} MT/Day","Actual": f"{summ['avg_daily_lsfo']} MT/Day"},
            {"Parameter": "Opening LSFO ROB",       "CP Warranted": "—",                              "Actual": f"{summ['opening_rob_lsfo']} MT"},
            {"Parameter": "Closing LSFO ROB",       "CP Warranted": "—",                              "Actual": f"{summ['closing_rob_lsfo']} MT"},
            {"Parameter": "Opening MGO ROB",        "CP Warranted": "—",                              "Actual": f"{summ['opening_rob_mgo']} MT"},
            {"Parameter": "Closing MGO ROB",        "CP Warranted": "—",                              "Actual": f"{summ['closing_rob_mgo']} MT"},
            {"Parameter": "Total Distance",         "CP Warranted": "—",                              "Actual": f"{summ['total_distance_nm']} nm"},
            {"Parameter": "Idle Days",              "CP Warranted": "—",                              "Actual": f"{summ['idle_days']} Days"},
        ])
        st.dataframe(comparison, use_container_width=True, hide_index=True)

# TAB 5 - CHARTS & VISUAL ANALYSIS
with tab5:
    st.header("Visual Analysis")
    st.write("Graphical breakdown of fuel consumption, speed, and weather data across the voyage.")
    
    st.subheader("Fuel & Speed Trends")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.image(chart_lsfo_vs_warranted(df), use_container_width=True)
    with col_c2:
        st.image(chart_rob_drawdown(df), use_container_width=True)

    col_c3, col_c4 = st.columns(2)
    with col_c3:
        st.image(chart_speed_vs_cp(df), use_container_width=True)
    with col_c4:
        st.image(chart_mgo_rob(df), use_container_width=True)

    st.subheader("Time & Fuel Breakdown")
    col_c5, col_c6 = st.columns(2)
    with col_c5:
        st.image(chart_time_utilisation(df), use_container_width=True)
    with col_c6:
        st.image(chart_lsfo_by_system(df), use_container_width=True)

    st.subheader("Weather Analysis")
    col_c7, col_c8 = st.columns(2)
    with col_c7:
        st.image(chart_beaufort(df), use_container_width=True)
    with col_c8:
        st.image(chart_wind_speed(df), use_container_width=True)

# TAB 6 - VOYAGE MAP
with tab6:
    st.header("Voyage Detail Map")
    st.write("Interactive spatial tracking of the vessel's reported positions.")

    def parse_coord(val):
        """Convert various coordinate formats to decimal degrees."""
        if val is None:
            return None
        val = str(val).strip()
        
        # Try direct float first
        try:
            return float(val)
        except ValueError:
            pass
        
        # Remove all spaces and extract components
        # Handles: '02 01.9 N', '01 17.9N', '104 49.7 E', '103 19.9'
        match = re.match(r"(\d+)\s*([\d.]+)\s*([NSEWnsew]?)", val)
        if match:
            deg    = float(match.group(1))
            mins   = float(match.group(2))
            hemi   = match.group(3).upper()
            result = deg + mins / 60
            if hemi in ("S", "W"):
                result = -result
            return round(result, 5)
        
        return None

    # Build coordinate list
    coords = []
    for _, row in df.iterrows():
        lat = parse_coord(row["latitude"])
        lon = parse_coord(row["longitude"])
        if lat and lon:
            coords.append({
                "date":      row["date"].strftime("%d-%b"),
                "lat":       lat,
                "lon":       lon,
                "operation": row["operation"],
                "remarks":   row["remarks"],
            })

    if coords:
        # Center map on midpoint
        center_lat = sum(c["lat"] for c in coords) / len(coords)
        center_lon = sum(c["lon"] for c in coords) / len(coords)

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles="CartoDB dark_matter"
        )

        # Draw route line
        if len(coords) > 1:
            folium.PolyLine(
                locations=[[c["lat"], c["lon"]] for c in coords],
                color="#0f9b8e",
                weight=2.5,
                dash_array="8 4",
                opacity=0.8
            ).add_to(m)

        # Add markers
        color_map = {"Idle": "orange", "Maneuvering": "yellow", "Steaming": "green"}
        for c in coords:
            folium.CircleMarker(
                location=[c["lat"], c["lon"]],
                radius=7,
                color=color_map.get(c["operation"], "white"),
                fill=True,
                fill_opacity=0.9,
                popup=folium.Popup(
                    f"<b>{c['date']}</b><br>{c['operation']}<br>{c['remarks'][:60]}...",
                    max_width=200
                ),
                tooltip=f"{c['date']} — {c['operation']}"
            ).add_to(m)

        # Show map
        st_folium(m, width=1200, height=500)

        # Coordinate table beside map
        st.subheader("Daily Positions")
        pos_df = pd.DataFrame([{
            "Date":      c["date"],
            "Latitude":  c["lat"],
            "Longitude": c["lon"],
            "Operation": c["operation"]
        } for c in coords])
        st.dataframe(pos_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No valid coordinates found in the data.")

# TAB 7 - ROUTE OPTIMIZER
with tab7:
    st.header("Route Optimizer")
    st.write("Compare the direct voyage path against a weather-optimized route for voyage planning.")

    from route_optimizer import (
        _great_circle_waypoints, _avoid_weather_waypoints,
        analyze_route, build_route_map
    )

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("Departure")
        dep_lat = st.number_input("Departure Latitude",  value=1.298, step=0.1, format="%.3f")
        dep_lon = st.number_input("Departure Longitude", value=103.332, step=0.1, format="%.3f")

    with col_r2:
        st.subheader("Destination")
        arr_lat = st.number_input("Arrival Latitude",   value=2.263, step=0.1, format="%.3f")
        arr_lon = st.number_input("Arrival Longitude",  value=101.998, step=0.1, format="%.3f")

    col_r3, col_r4 = st.columns(2)
    with col_r3:
        route_speed = st.number_input("Design Speed (kts)",       value=12.5, step=0.5)
    with col_r4:
        route_fuel  = st.number_input("Base Fuel Consumption (MT/day)", value=23.5, step=0.5)

    if st.button("Optimize Route", type="primary"):
        start = (dep_lat, dep_lon)
        end   = (arr_lat, arr_lon)

        # Compute both routes
        direct_wp  = _great_circle_waypoints(start, end, n=10)
        optimal_wp = _avoid_weather_waypoints(start, end, n=10)

        direct_res  = analyze_route(direct_wp,  route_speed, route_fuel)
        optimal_res = analyze_route(optimal_wp, route_speed, route_fuel)

        # Comparison metrics
        fuel_saved = round(direct_res["total_fuel"] - optimal_res["total_fuel"], 3)
        time_diff  = round(direct_res["total_hours"] - optimal_res["total_hours"], 1)

        st.subheader("Route Comparison")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Direct Route Fuel",   f"{direct_res['total_fuel']} MT")
        col_m2.metric("Optimized Fuel",      f"{optimal_res['total_fuel']} MT",
                      delta=f"{-fuel_saved} MT", delta_color="inverse")
        col_m3.metric("Direct ETA",          f"{direct_res['total_days']} days")
        col_m4.metric("Optimized ETA",       f"{optimal_res['total_days']} days",
                      delta=f"{round(-time_diff/24, 2)} days", delta_color="inverse")

        # Map
        st.subheader("Route Map")
        st.caption("Direct Route (Red Line)  |  Weather-Optimized Route (Green Line)  |  Weather Hazard Zones (Red Circles)")
        route_map = build_route_map(direct_res, optimal_res, start, end)
        st_folium(route_map, width=1200, height=500)

        # Segment detail
        st.subheader("Optimized Route — Segment Detail")
        seg_df = pd.DataFrame(optimal_res["segments"])
        seg_df.columns = ["From", "To", "Dist (nm)", "Wind (kts)", "Wave (m)", "Speed (kts)", "Fuel (MT)"]
        st.dataframe(seg_df, use_container_width=True, hide_index=True)


# GLOBAL EXPORT ACTION
st.divider()
st.header("Export Report")
st.write("Download a compiled PDF version of the current vessel performance data and charts.")

from report_generator import generate_pdf

if st.button("Generate & Download PDF", type="primary"):
    with st.spinner("Building PDF..."):
        pdf_bytes = generate_pdf(df, summ)
    st.download_button(
        label="Download PDF Report",
        data=pdf_bytes,
        file_name=f"Vessel_Performance_{summ['vessel_name'].replace(' ','_')}.pdf",
        mime="application/pdf"
    )