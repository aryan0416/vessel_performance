from fpdf import FPDF
import pandas as pd
import tempfile, os

from charts import (
    chart_lsfo_vs_warranted, chart_rob_drawdown,
    chart_speed_vs_cp, chart_mgo_rob,
    chart_time_utilisation, chart_lsfo_by_system,
    chart_beaufort, chart_wind_speed, chart_wave_height, chart_current_speed,
    chart_map_folium
)

# Brand Colors
DARK_NAVY  = (10, 25, 49)      # Sidebar and Headers
LIGHT_BG   = (244, 246, 249)   # Right side of cover page
TEAL       = (15, 155, 142)    # Accents
GOLD       = (240, 165, 0)
WHITE      = (255, 255, 255)
LGREY      = (240, 240, 240)
TEXT_GREY  = (90, 100, 110)
BLACK      = (30, 30, 30)
RED        = (231, 76, 60)
GREEN      = (46, 204, 113)

def _clean(txt):
    if pd.isna(txt): return ""
    txt = str(txt)
    replacements = {"–": "-", "—": "-", "→": "to", "·": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "★": "*"}
    for k, v in replacements.items(): txt = txt.replace(k, v)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

class VesselReport(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, _clean("Vessel Performance Report  ·  Apr 2026  ·  CONFIDENTIAL"), align="L")

def _save_chart(buf):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(buf.read())
    tmp.close()
    return tmp.name

def generate_pdf(df: pd.DataFrame, summary: dict) -> bytes:
    pdf = VesselReport(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Extract values safely
    vessel_name = summary.get("vessel_name", "M/V XYZ")
    voyage_from = summary.get("voyage_from", "Singapore EOPL")
    voyage_to   = summary.get("voyage_to", "Sungai Linggi")
    
    # ── PAGE 1: COVER ──────────────────────────────────────────────────────────
    pdf.add_page()
    # Left Sidebar (Dark Navy)
    pdf.set_fill_color(*DARK_NAVY)
    pdf.rect(0, 0, 95, 210, "F")
    
    # Right Content Area (Light Gray)
    pdf.set_fill_color(*LIGHT_BG)
    pdf.rect(95, 0, 202, 210, "F")

    # Left Sidebar Content
    pdf.set_text_color(*WHITE)
    pdf.set_xy(10, 40)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(75, 5, "VESSEL PERFORMANCE REPORT", align="C", ln=True)
    pdf.set_xy(10, 45)
    pdf.set_draw_color(*TEAL)
    pdf.set_line_width(0.8)
    pdf.line(25, 48, 70, 48)
    
    pdf.set_xy(10, 55)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(75, 10, _clean(vessel_name), align="C", ln=True)
    
    pdf.set_xy(10, 70)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(75, 5, "Ballast Voyage", align="C", ln=True)
    pdf.cell(75, 5, f"{voyage_from} to {voyage_to}", align="C", ln=True)

    # Sidebar Table
    pdf.set_y(95)
    items = [
        ("PERIOD", "22 Apr - 30 Apr 2026"),
        ("DELIVERY DATE\n& TIME", "22 APR 2026, 00:01 LT"),
        ("DATE", "May 02 , 2026"),
        ("CONDITION", "Ballast"),
        ("CP SPEED", "12.5 Kts (Eco)")
    ]
    for lbl, val in items:
        pdf.set_fill_color(15, 33, 62) # Slightly lighter navy for rows
        pdf.rect(0, pdf.get_y(), 95, 12, "F")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*GOLD)
        pdf.set_x(10)
        pdf.cell(30, 12, lbl)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*WHITE)
        pdf.cell(50, 12, val)
        pdf.ln(12)
        pdf.set_draw_color(0, 0, 0)
        pdf.line(0, pdf.get_y(), 95, pdf.get_y())

    # Right Side Content - Report Summary
    pdf.set_xy(105, 15)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*DARK_NAVY)
    pdf.cell(0, 10, "REPORT SUMMARY", ln=True)

    # KPI Tiles
    kpis = [
        ("Reporting Days", "9", "Days", TEAL),
        ("Total Distance", "234.03 nm", "Nautical Miles", TEAL),
        ("Avg Speed (Stmg)", "10.35 Kts", "CP Warranted: 12.5 Kts", RED),
        ("Idle at Anchor", "8", "Days (Sungai Linggi)", GOLD),
        ("LSFO Consumed", "46.987 MT", "Warranted: 49.5 MT", GREEN),
        ("LSFO ROB (Close)", "926.27 MT", "After reporting period", TEAL),
        ("MGO Consumed", "4.274 MT", "Total", TEAL),
        ("Avg Daily LSFO", "5.5 MT", "MT/Day", TEAL)
    ]
    
    x_start, y_start = 105, 30
    w, h, gap_x, gap_y = 42, 25, 4, 4
    
    for i, (title, val, sub, color) in enumerate(kpis):
        r, c = i // 4, i % 4
        x = x_start + c * (w + gap_x)
        y = y_start + r * (h + gap_y)
        
        pdf.set_fill_color(*WHITE)
        pdf.rect(x, y, w, h, "F")
        
        # Color bar
        pdf.set_fill_color(*color)
        pdf.rect(x, y, 2, h, "F")
        
        pdf.set_xy(x + 5, y + 3)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*TEXT_GREY)
        pdf.cell(w-5, 4, title, ln=True)
        
        pdf.set_x(x + 5)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*DARK_NAVY)
        pdf.cell(w-5, 8, val, ln=True)
        
        pdf.set_x(x + 5)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*TEXT_GREY)
        pdf.cell(w-5, 4, sub)

    # Narrative
    pdf.set_xy(105, 105)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*BLACK)
    narrative = [
        "Vessel anchored at Singapore EOPL on 22 Apr. LSFO ROB opened at 970.68 MT / MGO 242.98 MT.",
        "23 Apr: Vessel proceeded Sungai Linggi (Malacca manouvering) - 127.02 nm at avg 11.3 kts. Vessel was only maneuvering.",
        "24 Apr: Arrived Sungai Linggi (0215.8N, 10159.9E). Anchored awaiting load instructions - 7 days at anchor.",
        "No heavy weather recorded.",
        "Total Consumption LSFO: 46.987 MT  |  ME: 12.477 MT  |  AE: 25.05 MT  |  Boiler: 9.46 MT  |  MGO: 4.274 MT"
    ]
    for line in narrative:
        pdf.set_x(105)
        pdf.cell(4, 8, "-")
        pdf.multi_cell(180, 8, _clean(line))


    def draw_top_banner(title, date_range="Apr 22 - Apr 30, 2026"):
        pdf.set_fill_color(*DARK_NAVY)
        pdf.rect(0, 0, 297, 25, "F")
        pdf.set_xy(15, 8)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*WHITE)
        pdf.cell(150, 8, _clean(title))
        
        pdf.set_xy(150, 8)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*GOLD)
        pdf.cell(132, 5, date_range, align="R", ln=True)
        pdf.set_x(150)
        pdf.set_text_color(200, 200, 200)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(132, 5, "Singapore EOPL / Sungai Linggi", align="R")

    def section_bar(title, sub=""):
        pdf.set_fill_color(15, 33, 62) # Dark navy
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, f"  {title}", fill=True)
        if sub:
            pdf.set_x(120)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*TEXT_GREY)
            pdf.cell(0, 10, sub)
        pdf.ln()

    # ── PAGE 2: WARRANTED SPEED ────────────────────────────────────────────────
    pdf.add_page()
    draw_top_banner("VESSEL PERFORMANCE REPORT")
    pdf.set_y(30)
    section_bar("Warranted Speed & Consumption Table")
    
    col_w = [30, 30, 30, 30, 25, 30, 30, 30, 25]
    h1 = ["Speed", "RPM (Laden)", "M/E VLSFO\n(MT/Day)", "A/E FO\n(MT/Day)", "Boiler", "RPM (Ballast)", "M/E VLSFO\n(MT/Day)", "A/E FO\n(MT/Day)", "Boiler"]
    pdf.set_fill_color(15, 33, 62)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 8)
    
    # Header
    x_start = pdf.get_x()
    for w, h in zip(col_w, h1):
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(w, 5, h, border=1, align="C", fill=True)
        pdf.set_xy(x + w, y)
    pdf.ln(10)
    
    cp_speed = float(summary.get("cp_speed", 12.5))
    cp_lsfo = float(summary.get("cp_lsfo_steam", 26.5))
    data1 = []
    for i in range(6):
        s = cp_speed - i * 0.5
        cons = cp_lsfo * ((s / cp_speed)**3) if cp_speed > 0 else 0
        data1.append([
            f"{s:.1f} Kts{' * ECO' if i==0 else ''}", 
            f"{82-i}-{83-i}", 
            f"{cons:.1f}", "3", "0", 
            f"{79-i}-{80-i}", f"{cons*0.89:.1f}", "3", "0"
        ])
    pdf.set_font("Helvetica", "", 9)
    for i, row in enumerate(data1):
        pdf.set_fill_color(230, 245, 242) if i == 0 else pdf.set_fill_color(*WHITE)
        pdf.set_text_color(*TEAL) if i == 0 else pdf.set_text_color(*BLACK)
        for w, val in zip(col_w, row):
            pdf.cell(w, 8, _clean(val), border=1, align="C", fill=True)
        pdf.ln()

    pdf.ln(5)
    section_bar("PORT / SPECIAL OPERATION CONSUMPTION")
    col_w2 = [80, 40, 40, 30, 70]
    h2 = ["Operation", "VLSFO Total\n(MT/Day)", "A/E\n(MT/Day)", "Boiler\n(MT/Day)", "Remarks"]
    pdf.set_fill_color(25, 110, 110)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 8)
    for w, h in zip(col_w2, h2):
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(w, 5, h, border=1, align="C", fill=True)
        pdf.set_xy(x + w, y)
    pdf.ln(10)
    
    data2 = [
        ["Idle (in Port / at Anchorage) *", "5.5", "3", "2.5", "* APPLICABLE - this voyage"],
        ["Loading (including deballasting)", "7.8", "3", "4.8", "Condition depending"],
        ["Discharging (including running IG)", "32.0", "3", "29", "Condition depending"],
    ]
    pdf.set_font("Helvetica", "", 9)
    for i, row in enumerate(data2):
        pdf.set_fill_color(230, 245, 242) if i == 0 else pdf.set_fill_color(*WHITE)
        pdf.set_text_color(*GREEN) if i == 0 else pdf.set_text_color(*BLACK)
        for w, val in zip(col_w2, row):
            pdf.cell(w, 8, _clean(val), border=1, align="C", fill=True)
        pdf.ln()


    # ── PAGE 3: MASTER NOON REPORT ─────────────────────────────────────────────
    pdf.add_page()
    draw_top_banner("VESSEL PERFORMANCE REPORT")
    pdf.set_y(30)
    section_bar("Master Noon Report - Distance, Speed & Weather", "1200 LT daily position reports")
    
    col_w = [18, 20, 20, 15, 25, 15, 12, 12, 12, 12, 12, 12, 12, 12, 12, 15, 12, 12, 12]
    headers = ["Date","Latitude","Longitude","Post.","Operation","Cond.","Stm\nHrs","Dist\nnm","Avg\nSpd","CP\nSpd","RPM","Slip\n%","Wind\nDir","Wind\nSpd","BF","Wave\nmtrs","Swl\nDir","Swell\nmtr","Cur\nDir"]
    
    pdf.set_fill_color(*DARK_NAVY)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 7)
    for w, h in zip(col_w, headers):
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(w, 5, h, border=1, align="C", fill=True)
        pdf.set_xy(x + w, y)
    pdf.ln(10)
    
    # Mock daily data based on PDF
    data3 = [
        ["22-Apr", "02 01.9 N", "104 49.7 E", "At Port", "Idle", "Ballast", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"],
        ["23-Apr", "01 17.9 N", "103 19.9 E", "At Sea", "Manouvering", "Ballast", "0", "127.02", "11.3", "12.5", "80", "5.5", "5", "6", "2", "-", "-", "-", "8"],
        ["24-Apr", "02 15.8 N", "101 59.9 E", "At Port", "Idle/Manouvering", "Ballast", "0", "107.01", "11.7", "12.5", "0", "5.6", "5", "4", "2", "-", "-", "-", "11"],
        ["25-Apr", "02 15.8 N", "101 59.9 E", "At Port", "Idle", "Ballast", "0", "0", "11.7", "12.5", "0", "0", "8", "1", "3", "-", "-", "-", "4"],
    ]
    pdf.set_font("Helvetica", "", 7.5)
    for i, row in enumerate(data3):
        op = row[4]
        pdf.set_fill_color(253, 246, 227) if "Manouvering" in op else pdf.set_fill_color(*WHITE)
        pdf.set_text_color(*BLACK)
        for j, (w, val) in enumerate(zip(col_w, row)):
            if "Manouvering" in op and j==4: pdf.set_text_color(*GOLD)
            else: pdf.set_text_color(*BLACK)
            pdf.cell(w, 8, _clean(val), border=1, align="C", fill=True)
        pdf.ln()

    # ── PAGE 4: ENGINE SUMMARY - ROB & CONSUMPTION ─────────────────────────────
    pdf.add_page()
    draw_top_banner("VESSEL PERFORMANCE REPORT")
    pdf.set_y(30)
    section_bar("Engine Summary - ROB & Consumption", "No Additional Bunker yet received")
    
    # We will just print a simplified version matching the wide table
    headers4 = ["Date", "Lat.", "Long.", "Post.", "Operation", "Stm.\n(Hrs)", "Dist.\n(nm)", "Avg\nSpd.", "CP\nSpd.", "RPM", "Slip%", "ROB\nLSFO", "ROB\nMGO"]
    w4 = [18, 18, 18, 18, 25, 12, 12, 12, 12, 12, 12, 15, 15]
    pdf.set_fill_color(*DARK_NAVY)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 7)
    for w, h in zip(w4, headers4):
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(w, 6, h, border=1, align="C", fill=True)
        pdf.set_xy(x + w, y)
    pdf.ln(12)
    
    data4 = [
        ["22-Apr", "-", "-", "-", "Delivery", "-", "-", "-", "-", "-", "-", "973.56", "246.95"],
        ["22-Apr 12:00", "02 01.9N", "104 49.7E", "At Port", "Idle", "-", "-", "-", "-", "-", "-", "970.68", "242.98"],
    ]
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_fill_color(*WHITE)
    pdf.set_text_color(*BLACK)
    for row in data4:
        for w, val in zip(w4, row):
            pdf.cell(w, 8, _clean(val), border=1, align="C", fill=True)
        pdf.ln()

    # ── PAGE 5: VOYAGE SUMMARY ────────────────────────────────────────────────
    pdf.add_page()
    draw_top_banner("VESSEL PERFORMANCE REPORT")
    pdf.set_y(30)
    section_bar("Voyage Summary - Actuals vs Charter Party Warranted")
    
    # Mock rendering side-by-side or stacked
    # Stacked for simplicity and accuracy
    pdf.ln(5)
    
    # Table 2: Parameter | CP Warranted | Actual
    pdf.set_x(145)
    y_start = pdf.get_y()
    pdf.set_fill_color(30, 130, 120)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(40, 8, "Parameter", 1, 0, "C", True)
    pdf.cell(40, 8, "CP Warranted", 1, 0, "C", True)
    pdf.cell(40, 8, "Actual", 1, 1, "C", True)
    
    t5 = [
        ("Speed (Steaming Avg)", "12.5 Kts", "10.35 Kts"),
        ("Total LSFO Consumed", "49.5 MT", "46.987 MT"),
        ("Avg. Daily LSFO", "5.5 MT/Day", "5.5 MT/Day"),
    ]
    pdf.set_font("Helvetica", "", 9)
    for row in t5:
        pdf.set_x(145)
        pdf.set_fill_color(*WHITE)
        pdf.set_text_color(*BLACK)
        pdf.cell(40, 8, row[0], 1, 0, "C", True)
        pdf.set_text_color(*TEXT_GREY)
        pdf.cell(40, 8, row[1], 1, 0, "C", True)
        pdf.set_text_color(*GREEN)
        pdf.cell(40, 8, row[2], 1, 1, "C", True)


    # ── PAGE 6: ENGINE SUMMARY & BUNKER ROB ──────────────────────────────────
    pdf.add_page()
    draw_top_banner("VESSEL PERFORMANCE REPORT")
    pdf.set_y(30)
    section_bar("Engine Summary - Consumption & Bunker ROB", "Daily bunker consumption breakdown")
    
    # Right side table for Bunker ROB
    pdf.set_xy(200, 45)
    pdf.set_fill_color(*DARK_NAVY)
    pdf.set_text_color(*GOLD)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(80, 8, "BUNKER ROB SUMMARY", 0, 1, "C", True)
    
    rob = [
        ("Opening LSFO ROB", "970.68 MT"),
        ("Closing LSFO ROB", "926.27 MT"),
        ("Total LSFO Consumed", "46.987 MT"),
        ("Warranted LSFO", "49.5 MT"),
    ]
    pdf.set_font("Helvetica", "", 9)
    for k, v in rob:
        pdf.set_x(200)
        pdf.set_text_color(*TEXT_GREY)
        pdf.cell(50, 8, k, 0, 0, "L")
        pdf.set_text_color(*TEAL)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(30, 8, v, 0, 1, "R")
        pdf.set_font("Helvetica", "", 9)

    # ── PAGE 7, 8, 9: CHARTS ──────────────────────────────────────────────────
    def place_charts(title, chart_funcs):
        pdf.add_page()
        draw_top_banner("VESSEL PERFORMANCE REPORT")
        pdf.set_y(30)
        section_bar(title)
        
        paths = [_save_chart(f(df, theme="light")) for f in chart_funcs]
        
        if len(paths) == 4:
            pdf.image(paths[0], x=15, y=45, w=130)
            pdf.image(paths[1], x=150, y=45, w=130)
            pdf.image(paths[2], x=15, y=125, w=130)
            pdf.image(paths[3], x=150, y=125, w=130)
        elif len(paths) == 2:
            pdf.image(paths[0], x=20, y=50, w=120)
            pdf.image(paths[1], x=150, y=50, w=120)
            
        for p in paths: os.unlink(p)

    place_charts("Visual Analysis - Fuel ROB & Daily Consumption Trends", 
                 [chart_lsfo_vs_warranted, chart_rob_drawdown, chart_speed_vs_cp, chart_mgo_rob])
                 
    place_charts("Time Utilization & Fuel Efficiency", 
                 [chart_time_utilisation, chart_lsfo_by_system])
                 
    place_charts("Weather Analysis - Reported vs Actual | Wave, Wind Speed & Current", 
                 [chart_beaufort, chart_wind_speed, chart_wave_height, chart_current_speed])

    # ── PAGE 10: VOYAGE MAP ──────────────────────────────────────────────────
    pdf.add_page()
    draw_top_banner("VESSEL PERFORMANCE REPORT")
    pdf.set_y(30)
    section_bar("Voyage Detail Map")
    
    map_path = _save_chart(chart_map_folium(df))
    pdf.image(map_path, x=15, y=45, w=260)
    os.unlink(map_path)

    # Output
    out = pdf.output(dest="S")
    if isinstance(out, str): return out.encode("latin-1")
    return bytes(out)