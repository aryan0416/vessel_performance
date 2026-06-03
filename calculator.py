import pandas as pd

def calculate_performance(df: pd.DataFrame, cp: dict) -> pd.DataFrame:
    """
    Adds performance comparison columns to the dataframe.
    
    cp dict keys:
        cp_speed        - warranted steaming speed (knots)
        cp_lsfo_idle    - warranted LSFO when idle (MT/day)
        cp_lsfo_steam   - warranted LSFO when steaming (MT/day)
        opening_rob_lsfo - LSFO ROB at start of voyage
        opening_rob_mgo  - MGO ROB at start of voyage
    """

    df = df.copy()

    # Determine operation type per day
    def get_operation(row):
        remarks = row["remarks"].lower()
        dist    = row["engine_distance"]

        # Anchored/waiting/idle keywords override everything
        idle_keywords = ["anchor", "waiting", "idle", "at port", "eopl", "surveyor"]
        if any(k in remarks for k in idle_keywords):
            return "Idle"

        if "maneuver" in remarks or "maneuvering" in remarks:
            return "Maneuvering"

        if dist > 50:
            return "Steaming"

        return "Idle"

    df["operation"] = df.apply(get_operation, axis=1)
    df.loc[df["operation"] == "Idle", "avg_speed"] = 0.0

    # Warranted LSFO per day based on operation
    def get_warranted_lsfo(row):
        if row["operation"] == "Steaming":
            return cp["cp_lsfo_steam"]
        elif row["operation"] == "Maneuvering":
            return cp["cp_lsfo_steam"]   # maneuvering uses same as steaming
        else:
            return cp["cp_lsfo_idle"]

    df["warranted_lsfo"] = df.apply(get_warranted_lsfo, axis=1)

    # Speed performance
    df["cp_speed"] = cp["cp_speed"]
    df["speed_diff"] = df["avg_speed"] - cp["cp_speed"]  # negative = underperforming

    # LSFO performance (negative = saved fuel, positive = excess consumption)
    df["lsfo_diff"] = df["total_lsfo"] - df["warranted_lsfo"]

    # Performance flags
    df["speed_ok"]  = df["avg_speed"] >= cp["cp_speed"]
    df["lsfo_ok"]   = df["total_lsfo"] <= df["warranted_lsfo"]

    # Recalculate ROB from scratch using opening ROB
    # (Excel had formulas that weren't evaluated — we recompute cleanly)
    rob_lsfo = cp["opening_rob_lsfo"]
    rob_mgo  = cp["opening_rob_mgo"]
    computed_rob_lsfo = []
    computed_rob_mgo  = []

    for _, row in df.iterrows():
        lsfo_recv = row.get("lsfo_received", 0.0)
        mgo_recv  = row.get("mgo_received", 0.0)
        
        # Handle NaN values explicitly
        if pd.isna(lsfo_recv): lsfo_recv = 0.0
        if pd.isna(mgo_recv):  mgo_recv = 0.0
        
        rob_lsfo = rob_lsfo + lsfo_recv - row.get("total_lsfo", 0.0)
        rob_mgo  = rob_mgo  + mgo_recv  - row.get("total_mgo", 0.0)
        computed_rob_lsfo.append(round(rob_lsfo, 3))
        computed_rob_mgo.append(round(rob_mgo, 3))

    df["computed_rob_lsfo"] = computed_rob_lsfo
    df["computed_rob_mgo"]  = computed_rob_mgo

    return df


def get_summary(df: pd.DataFrame, cp: dict) -> dict:
    """
    Returns a dict of all KPI values for the summary page.
    """
    steaming_days = df[df["operation"] == "Steaming"]
    idle_days     = df[df["operation"] == "Idle"]
    maneuver_days = df[df["operation"] == "Maneuvering"]

    total_distance   = df["engine_distance"].sum()
    total_lsfo       = round(df["total_lsfo"].sum(), 3)
    total_mgo        = round(df["total_mgo"].sum(), 3)
    reporting_days   = len(df)

    # Average speed only over steaming + maneuvering days
    moving = df[df["operation"].isin(["Steaming", "Maneuvering"])]
    avg_speed = round(moving["avg_speed"].mean(), 2) if len(moving) > 0 else 0.0

    # Warranted totals
    warranted_lsfo = round(df["warranted_lsfo"].sum(), 3)

    # Opening and closing ROB
    opening_rob_lsfo = cp["opening_rob_lsfo"]
    closing_rob_lsfo = round(df["computed_rob_lsfo"].iloc[-1], 3)
    opening_rob_mgo  = cp["opening_rob_mgo"]
    closing_rob_mgo  = round(df["computed_rob_mgo"].iloc[-1], 3)

    # Daily average LSFO
    avg_daily_lsfo = round(total_lsfo / reporting_days, 3) if reporting_days > 0 else 0.0

    return {
        "vessel_name":        cp.get("vessel_name", "M/V Unknown"),
        "voyage_from":        cp.get("voyage_from", "-"),
        "voyage_to":          cp.get("voyage_to", "-"),
        "period_start":       df["date"].iloc[0].strftime("%d %b %Y"),
        "period_end":         df["date"].iloc[-1].strftime("%d %b %Y"),
        "reporting_days":     reporting_days,
        "total_distance_nm":  round(total_distance, 2),
        "avg_speed":          avg_speed,
        "cp_speed":           cp["cp_speed"],
        "idle_days":          len(idle_days),
        "steaming_days":      len(steaming_days),
        "maneuvering_days":   len(maneuver_days),
        "total_lsfo":         total_lsfo,
        "warranted_lsfo":     warranted_lsfo,
        "lsfo_diff":          round(total_lsfo - warranted_lsfo, 3),
        "total_mgo":          total_mgo,
        "avg_daily_lsfo":     avg_daily_lsfo,
        "cp_daily_lsfo":      cp["cp_lsfo_idle"],
        "opening_rob_lsfo":   opening_rob_lsfo,
        "closing_rob_lsfo":   closing_rob_lsfo,
        "opening_rob_mgo":    opening_rob_mgo,
        "closing_rob_mgo":    closing_rob_mgo,
    }


def generate_narrative(df: pd.DataFrame, summary: dict) -> str:
    """
    Auto-generates a voyage narrative paragraph like a real analyst would write.
    """
    lines = []

    # Opening ROB line
    lines.append(
        f"Vessel commenced reporting period on {summary['period_start']} with "
        f"LSFO ROB of {summary['opening_rob_lsfo']} MT and MGO ROB of {summary['opening_rob_mgo']} MT."
    )

    # Day by day narrative
    for _, row in df.iterrows():
        date    = row["date"].strftime("%d %b")
        op      = row["operation"]
        remarks = row["remarks"].strip()
        dist    = row["engine_distance"]
        speed   = row["avg_speed"]
        lsfo    = round(row["total_lsfo"], 3)

        if op == "Maneuvering":
            lines.append(
                f"{date}: Vessel maneuvering — {round(dist, 1)} nm at avg {speed} kts. "
                f"LSFO consumed: {lsfo} MT. {remarks}."
            )
        elif op == "Steaming":
            lines.append(
                f"{date}: Vessel steaming — {round(dist, 1)} nm at avg {speed} kts. "
                f"LSFO consumed: {lsfo} MT. {remarks}."
            )
        else:
            lines.append(
                f"{date}: Vessel idle — {remarks}. LSFO consumed: {lsfo} MT."
            )

    # Performance assessment
    speed_diff = round(summary["avg_speed"] - summary["cp_speed"], 2)
    lsfo_diff  = summary["lsfo_diff"]

    if speed_diff < 0:
        lines.append(
            f"Speed Performance: Vessel averaged {summary['avg_speed']} kts against CP warranted "
            f"{summary['cp_speed']} kts — {abs(speed_diff)} kts below warranted."
        )
    else:
        lines.append(
            f"Speed Performance: Vessel averaged {summary['avg_speed']} kts, meeting CP warranted speed."
        )

    if lsfo_diff < 0:
        lines.append(
            f"Fuel Performance: Total LSFO consumed {summary['total_lsfo']} MT against warranted "
            f"{summary['warranted_lsfo']} MT — saved {abs(round(lsfo_diff, 3))} MT."
        )
    else:
        lines.append(
            f"Fuel Performance: Total LSFO consumed {summary['total_lsfo']} MT against warranted "
            f"{summary['warranted_lsfo']} MT — excess consumption of {round(lsfo_diff, 3)} MT."
        )

    # Closing ROB
    lines.append(
        f"Closing ROB: LSFO {summary['closing_rob_lsfo']} MT | MGO {summary['closing_rob_mgo']} MT."
    )

    return "\n\n".join(lines)


# Quick test
if __name__ == "__main__":
    from parser import parse_noon_report, get_vessel_info
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "NOON REPORT- SAMPLE.xlsx"

    df   = parse_noon_report(path)
    info = get_vessel_info(path)

    cp = {
        "vessel_name":       info["vessel_name"],
        "voyage_from":       "Singapore EOPL",
        "voyage_to":         "Sungai Linggi",
        "cp_speed":          12.5,
        "cp_lsfo_steam":     23.5,
        "cp_lsfo_idle":      5.5,
        "opening_rob_lsfo":  970.68,
        "opening_rob_mgo":   242.98,
    }

    result  = calculate_performance(df, cp)
    summary = get_summary(result, cp)

    print("\n=== DAILY PERFORMANCE ===")
    print(result[[
        "date", "operation", "avg_speed", "cp_speed",
        "speed_diff", "total_lsfo", "warranted_lsfo",
        "lsfo_diff", "computed_rob_lsfo"
    ]].to_string())

    print("\n=== VOYAGE SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k:<25} {v}")