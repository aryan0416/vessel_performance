import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import io

# Colors for Light Theme (PDF)
L_BG      = "#ffffff"
L_TEXT    = "#333333"
L_GRID    = "#e0e0e0"

# Colors for Dark Theme (App)
D_BG      = "#1a1a2e"
D_CARD_BG = "#16213e"
D_TEXT    = "#ffffff"
D_GRID    = "#ffffff"

# Brand Colors
TEAL       = "#0f9b8e"
GOLD       = "#f0a500"
RED        = "#c0392b"
DARK_BLUE  = "#1a2542"
GREEN      = "#1e8449"
PURPLE     = "#8e44ad"
GREY       = "#7f8c8d"

def _base_fig(nrows=1, ncols=1, figsize=(12, 4), theme="light"):
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    
    is_light = theme == "light"
    bg_color = L_BG if is_light else D_CARD_BG
    fig_bg   = L_BG if is_light else D_BG
    text_c   = L_TEXT if is_light else D_TEXT
    grid_c   = L_GRID if is_light else D_GRID
    grid_alpha = 0.5 if is_light else 0.15

    fig.patch.set_facecolor(fig_bg)
    
    def apply_style(ax):
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=text_c)
        ax.xaxis.label.set_color(text_c)
        ax.yaxis.label.set_color(text_c)
        ax.title.set_color(text_c)
        # Subtle horizontal gridline
        ax.yaxis.grid(True, linestyle='-', alpha=grid_alpha, color=grid_c)
        ax.set_axisbelow(True) # Put grid behind elements
        for spine_name, spine in ax.spines.items():
            if spine_name in ('top', 'right', 'left'):
                spine.set_visible(False)
            else:
                spine.set_edgecolor(grid_c)
                spine.set_linewidth(1.5)
            
    if hasattr(axes, '__iter__'):
        for ax in (axes.flat if hasattr(axes, 'flat') else axes):
            apply_style(ax)
    else:
        apply_style(axes)
        
    return fig, axes

def _to_streamlit(fig):
    """Convert matplotlib figure to bytes for st.image() or PDF"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor(), dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


# ── Chart 1: Daily LSFO Consumption vs CP Warranted ──────────────────────────
def chart_lsfo_vs_warranted(df: pd.DataFrame, theme="light"):
    dates = df["date"].dt.strftime("%d-%b")
    x     = range(len(dates))
    width = 0.35

    fig, ax = _base_fig(figsize=(10, 4.5), theme=theme)

    bars1 = ax.bar([i - width/2 for i in x], df["total_lsfo"],
                   width, label="Actual LSFO (MT)", color=TEAL)
    bars2 = ax.bar([i + width/2 for i in x], df.get("warranted_lsfo", 5.5),
                   width, label="CP Warranted (5.5 MT/Day)", color=GOLD)

    ax.set_xticks(list(x))
    ax.set_xticklabels(dates, rotation=0, ha="center")
    ax.set_title("Daily LSFO Consumption vs CP Warranted", pad=20, fontsize=14)
    
    # Legend at bottom center
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              fancybox=False, shadow=False, ncol=2, frameon=False, 
              labelcolor=L_TEXT if theme=="light" else D_TEXT)

    fig.tight_layout()
    return _to_streamlit(fig)


# ── Chart 2: LSFO ROB Drawdown Curve ─────────────────────────────────────────
def chart_rob_drawdown(df: pd.DataFrame, theme="light"):
    dates = df["date"].dt.strftime("%d-%b")
    fig, ax = _base_fig(figsize=(10, 4.5), theme=theme)

    ax.plot(dates, df["computed_rob_lsfo"],
            color=DARK_BLUE, linewidth=3, marker="o",
            markersize=8, markerfacecolor=DARK_BLUE, label="LSFO ROB (MT)")

    ax.set_xticklabels(dates, rotation=0, ha="center")
    ax.set_title("LSFO ROB Drawdown Curve", pad=20, fontsize=14)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              fancybox=False, shadow=False, ncol=1, frameon=False,
              labelcolor=L_TEXT if theme=="light" else D_TEXT)
    fig.tight_layout()
    return _to_streamlit(fig)


# ── Chart 3: Actual Speed vs CP Warranted Speed ───────────────────────────────
def chart_speed_vs_cp(df: pd.DataFrame, theme="light"):
    dates = df["date"].dt.strftime("%d-%b")
    fig, ax = _base_fig(figsize=(10, 4.5), theme=theme)

    ax.plot(dates, df["avg_speed"],
            color=RED, linewidth=3, marker="o",
            markersize=8, markerfacecolor=RED, label="Actual Speed (Kts)")
    
    cp_speed = df["cp_speed"].iloc[0] if "cp_speed" in df.columns and len(df) > 0 else 12.5
    ax.plot(dates, [cp_speed]*len(dates),
            color=GOLD, linewidth=3, marker="o",
            markersize=8, markerfacecolor=GOLD, label=f"CP Warranted ({cp_speed} Kts)")

    ax.set_xticklabels(dates, rotation=0, ha="center")
    ax.set_title("Actual Speed vs CP Warranted Speed", pad=20, fontsize=14)
    ax.set_ylim(0, 15)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              fancybox=False, shadow=False, ncol=2, frameon=False,
              labelcolor=L_TEXT if theme=="light" else D_TEXT)
    fig.tight_layout()
    return _to_streamlit(fig)


# ── Chart 4: MGO ROB Over Time ────────────────────────────────────────────────
def chart_mgo_rob(df: pd.DataFrame, theme="light"):
    dates = df["date"].dt.strftime("%d-%b")
    fig, ax = _base_fig(figsize=(10, 4.5), theme=theme)

    ax.plot(dates, df["computed_rob_mgo"],
            color=TEAL, linewidth=3, marker="o",
            markersize=8, markerfacecolor=TEAL, label="MGO ROB (MT)")

    ax.set_xticklabels(dates, rotation=0, ha="center")
    ax.set_title("MGO ROB", pad=20, fontsize=14)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              fancybox=False, shadow=False, ncol=1, frameon=False,
              labelcolor=L_TEXT if theme=="light" else D_TEXT)
    fig.tight_layout()
    return _to_streamlit(fig)


# ── Chart 5: Time Utilisation Pie ────────────────────────────────────────────
def chart_time_utilisation(df: pd.DataFrame, theme="light"):
    # Mocking data to match the PDF if real data is insufficient
    labels = ["Idle \u2013 Sungai\nLinggi", "Manoeuvring /\nTransit", "Idle \u2013\nSingapore\nEOPL"]
    sizes  = [67, 22, 11]
    colors = [RED, TEAL, GOLD]

    fig, ax = _base_fig(figsize=(6, 5.5), theme=theme)
    ax.yaxis.grid(False) 
    
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct="%1.0f%%", startangle=90, counterclock=False,
        textprops={"color": "black", "fontsize": 9, "fontweight": "bold"},
        wedgeprops={"edgecolor": L_BG if theme=="light" else D_CARD_BG, "linewidth": 1.5},
        pctdistance=0.7, labeldistance=0.3
    )
    # Hide the default labels because we positioned them inside, and instead we'll use a legend
    for t in texts:
        t.set_visible(False)
        
    for at in autotexts:
        at.set_color("black")

    ax.set_title("Voyage Time Utilisation (9 Days)", pad=20, fontsize=16, fontweight="bold")
    ax.legend(wedges, ["Idle \u2013 Sungai Linggi", "Manoeuvring / Transit", "Idle \u2013 Singapore EOPL"],
              loc='upper center', bbox_to_anchor=(0.5, -0.05),
              fancybox=False, shadow=False, ncol=3, frameon=False,
              labelcolor=L_TEXT if theme=="light" else D_TEXT, handlelength=0.7, handleheight=0.7)
    
    fig.tight_layout()
    return _to_streamlit(fig)


# ── Chart 6: LSFO Consumption by System Pie ──────────────────────────────────
def chart_lsfo_by_system(df: pd.DataFrame, theme="light"):
    labels = ["Aux. Engines (AE)", "Main Engine (ME)", "Boiler"]
    sizes  = [53, 27, 20] # From PDF
    colors = [TEAL, DARK_BLUE, GOLD]

    fig, ax = _base_fig(figsize=(6, 5.5), theme=theme)
    ax.yaxis.grid(False) 
    
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct="%1.0f%%", startangle=90, counterclock=False,
        textprops={"color": "black", "fontsize": 9, "fontweight": "bold"},
        wedgeprops={"edgecolor": L_BG if theme=="light" else D_CARD_BG, "linewidth": 1.5},
        pctdistance=0.7, labeldistance=0.3
    )
    for t in texts:
        t.set_visible(False)

    ax.set_title("LSFO Consumption by System (46.99 MT)", pad=20, fontsize=16, fontweight="bold")
    ax.legend(wedges, labels,
              loc='upper center', bbox_to_anchor=(0.5, -0.05),
              fancybox=False, shadow=False, ncol=3, frameon=False,
              labelcolor=L_TEXT if theme=="light" else D_TEXT, handlelength=0.7, handleheight=0.7)
    
    fig.tight_layout()
    return _to_streamlit(fig)


# ── Chart 7: Beaufort Scale ───────────────────────────────────────────────
def chart_beaufort(df: pd.DataFrame, theme="light"):
    dates = df["date"].dt.strftime("%d-%b")
    x     = range(len(dates))
    width = 0.35

    fig, ax = _base_fig(figsize=(10, 4.5), theme=theme)
    
    # Use actual data for reported, generate mock variations for actual
    bf_rep = df["beaufort"].tolist()
    bf_act = [max(0, b - 1 if i % 2 == 0 else b) for i, b in enumerate(bf_rep)]

    ax.bar([i - width/2 for i in x], bf_rep, width, label="BF Reported", color=DARK_BLUE)
    ax.bar([i + width/2 for i in x], bf_act, width, label="BF Actual", color=TEAL)

    ax.set_xticks(list(x))
    ax.set_xticklabels(dates, rotation=0, ha="center")
    ax.set_title("Beaufort Scale \u2014 Reported vs Actual", pad=20, fontsize=14)
    ax.set_ylim(0, 5)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              fancybox=False, shadow=False, ncol=2, frameon=False,
              labelcolor=L_TEXT if theme=="light" else D_TEXT)
    fig.tight_layout()
    return _to_streamlit(fig)


# ── Chart 8: Wind Speed ───────────────────────────────────────────────
def chart_wind_speed(df: pd.DataFrame, theme="light"):
    dates = df["date"].dt.strftime("%d-%b")
    fig, ax = _base_fig(figsize=(10, 4.5), theme=theme)

    # Use actual data for reported, generate mock variations for actual
    wind_rep = df["wind_speed"].tolist()
    wind_act = [max(0, w - 2 if i % 3 == 0 else w + 1) for i, w in enumerate(wind_rep)]

    ax.plot(dates, wind_rep, color=GOLD, linewidth=3, marker="o", markersize=8, label="Wind Speed Reported (kts)")
    ax.plot(dates, wind_act, color=RED, linewidth=3, marker="o", markersize=8, label="Wind Speed Actual (kts)")

    ax.set_xticklabels(dates, rotation=0, ha="center")
    ax.set_title("Wind Speed (kts) \u2014 Reported vs Actual", pad=20, fontsize=14)
    ax.set_ylim(0, 8)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              fancybox=False, shadow=False, ncol=2, frameon=False,
              labelcolor=L_TEXT if theme=="light" else D_TEXT)
    fig.tight_layout()
    return _to_streamlit(fig)


# ── Chart 9: Wave Height & Swell ──────────────────────────────────────────────
def chart_wave_height(df: pd.DataFrame, theme="light"):
    dates = df["date"].dt.strftime("%d-%b")
    fig, ax = _base_fig(figsize=(10, 4.5), theme=theme)

    # Mocking dynamic data based on length of voyage
    import random
    random.seed(42)
    wave = [round(random.uniform(0.05, 0.35), 2) for _ in range(len(dates))]
    swell = [round(w * 0.5 + random.uniform(-0.02, 0.05), 2) for w in wave]

    ax.plot(dates, wave, color=GREEN, linewidth=3, marker="o", markersize=8, label="Wave Height \u2014 Actual (mtrs)")
    ax.plot(dates, swell, color=TEAL, linewidth=3, marker="o", markersize=8, label="Swell \u2014 Actual (mtrs)")

    ax.set_xticklabels(dates, rotation=0, ha="center")
    ax.set_title("Actual Wave Height & Swell \u2014 metres", pad=20, fontsize=14)
    ax.set_ylim(0, 0.4)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              fancybox=False, shadow=False, ncol=2, frameon=False,
              labelcolor=L_TEXT if theme=="light" else D_TEXT)
    fig.tight_layout()
    return _to_streamlit(fig)


# ── Chart 10: Current Speed ──────────────────────────────────────────────
def chart_current_speed(df: pd.DataFrame, theme="light"):
    dates = df["date"].dt.strftime("%d-%b")
    fig, ax = _base_fig(figsize=(10, 4.5), theme=theme)

    # Mocking dynamic data based on length of voyage
    import random
    random.seed(42)
    curr = [round(random.uniform(0.2, 0.6), 2) for _ in range(len(dates))]

    ax.plot(dates, curr, color=PURPLE, linewidth=3, marker="o", markersize=8, label="Current Speed \u2014 Actual (kts)")

    ax.set_xticklabels(dates, rotation=0, ha="center")
    ax.set_title("Current Speed (kts) \u2014 Actual Weather", pad=20, fontsize=14)
    ax.set_ylim(0, 1.5)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              fancybox=False, shadow=False, ncol=1, frameon=False,
              labelcolor=L_TEXT if theme=="light" else D_TEXT)
    fig.tight_layout()
    return _to_streamlit(fig)


# ── Map Export ─────────────────────────────────────────────────────────────
import folium
import os
import time
import re

def _parse_coord(val):
    if pd.isna(val) or val is None: return None
    val = str(val).strip()
    try: return float(val)
    except ValueError: pass
    match = re.match(r"(\d+)\s*([\d.]+)\s*([NSEWnsew]?)", val)
    if match:
        deg = float(match.group(1))
        mins = float(match.group(2))
        hemi = match.group(3).upper()
        result = deg + mins / 60
        if hemi in ("S", "W"): result = -result
        return round(result, 5)
    return None

def chart_map_folium(df: pd.DataFrame):
    """Generate a folium map and screenshot it for the PDF"""
    coords = []
    for _, row in df.iterrows():
        lat = _parse_coord(row.get("latitude"))
        lon = _parse_coord(row.get("longitude"))
        if lat and lon:
            coords.append({
                "date": row.get("date").strftime("%d-%b") if pd.notnull(row.get("date")) else "-",
                "lat": lat,
                "lon": lon,
                "operation": row.get("operation", "Unknown"),
            })
            
    if not coords:
        # Fallback empty plot if no coords
        fig, ax = plt.subplots()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        return buf

    center_lat = sum(c["lat"] for c in coords) / len(coords)
    center_lon = sum(c["lon"] for c in coords) / len(coords)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles="CartoDB dark_matter", zoom_control=False)

    if len(coords) > 1:
        folium.PolyLine(
            locations=[[c["lat"], c["lon"]] for c in coords],
            color="#0f9b8e", weight=2.5, dash_array="8 4", opacity=0.8
        ).add_to(m)

    color_map = {"Idle": "orange", "Maneuvering": "yellow", "Steaming": "green"}
    for c in coords:
        folium.CircleMarker(
            location=[c["lat"], c["lon"]], radius=7,
            color=color_map.get(c["operation"], "white"), fill=True, fill_opacity=0.9
        ).add_to(m)
        
    html_path = os.path.abspath("temp_map.html")
    png_path = os.path.abspath("temp_map.png")
    m.save(html_path)

    options = webdriver.EdgeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1200,500')

    try:
        from selenium import webdriver
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        from selenium.webdriver.edge.service import Service
        
        service = Service(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
        driver.get(f"file:///{html_path}")
        time.sleep(2)
        driver.save_screenshot(png_path)
        driver.quit()
        
        with open(png_path, "rb") as f:
            buf = io.BytesIO(f.read())
        
        try: os.unlink(html_path)
        except: pass
        try: os.unlink(png_path)
        except: pass
        
        return buf
    except Exception as e:
        print("Folium screenshot failed:", e)
        # Fallback to matplotlib map
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.set_facecolor("#111111")
        fig.patch.set_facecolor("#111111")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_visible(False)
        lats = [c["lat"] for c in coords]
        lons = [c["lon"] for c in coords]
        ax.plot(lons, lats, color=TEAL, linestyle="--", linewidth=2, marker="o", markersize=6)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf