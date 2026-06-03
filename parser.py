import pandas as pd
import numpy as np
import re

def _find_header_row_index(filepath, anchor_keyword="Date", max_rows=50):
    """Fallback legacy function."""
    try:
        df_top = pd.read_excel(filepath, header=None, nrows=max_rows)
        for idx, row in df_top.iterrows():
            row_vals = row.astype(str).str.lower().str.strip()
            if anchor_keyword.lower() in row_vals.values:
                return idx
    except Exception as e:
        pass
    return 0

def get_vessel_info(filepath):
    info = {"vessel_name": "Unknown", "voyage": "Unknown"}
    with pd.ExcelFile(filepath) as xl:
        for sheet in xl.sheet_names:
            df_meta = xl.parse(sheet, header=None, nrows=20)
            for _, row in df_meta.iterrows():
                row_strs = row.astype(str).str.lower()
                for col_idx, cell_val in enumerate(row_strs):
                    if "vessel" in cell_val or "m/v" in cell_val:
                        if col_idx + 1 < len(row):
                            potential_name = str(row.iloc[col_idx + 1]).strip()
                            if potential_name and potential_name != "nan":
                                info["vessel_name"] = potential_name.upper()
                                return info
    return info

def parse_noon_report(filepath):
    all_dfs = []
    
    with pd.ExcelFile(filepath) as xl:
        for sheet in xl.sheet_names:
            df_raw = xl.parse(sheet, header=None)
            is_transposed = False
            
            # Check for transposed format first
            for c in range(min(5, len(df_raw.columns))):
                if df_raw.iloc[:, c].astype(str).str.contains('UTC DATE', case=False, na=False).any():
                    is_transposed = True
                    
                    # Headers are in column c
                    raw_headers = df_raw.iloc[:, c].astype(str).str.strip().str.lower()
                    headers = []
                    for h in raw_headers:
                        h = h.replace(' ', '_').replace('\n', '')
                        h = h.replace('(mt)', '').replace('_(mt)', '').replace('(%)', 'pct')
                        h = h.strip('_')
                        headers.append(h)
                    
                    data = df_raw.iloc[:, c+1:].T
                    data.columns = headers
                    data = data.loc[:, ~data.columns.duplicated()]
                    all_dfs.append(data)
                    break
                    
            if not is_transposed:
                # Try traditional row-based format
                h_idx = -1
                for idx, row in df_raw.head(50).iterrows():
                    row_vals = row.astype(str).str.lower().str.strip().values
                    if "date" in row_vals or "utc date" in row_vals:
                        h_idx = idx
                        break
                
                if h_idx >= 0:
                    df_sheet = xl.parse(sheet, header=h_idx)
                    df_sheet.columns = [str(c).strip().lower().replace(" ", "_").replace("\n", "") for c in df_sheet.columns]
                    df_sheet = df_sheet.loc[:, ~df_sheet.columns.duplicated()]
                    all_dfs.append(df_sheet)

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs, ignore_index=True)

    column_mapping = {
        "date": "date",
        "utc_date": "date",
        "lat": "latitude",
        "latitude": "latitude",
        "long": "longitude",
        "longitude": "longitude",
        "ops": "operation",
        "operation": "operation",
        "status": "operation",
        "vessel_condition": "operation",
        "dist": "engine_distance",
        "distance": "engine_distance",
        "engine_dist": "engine_distance",
        "engine_distance_24_hrs": "engine_distance",
        "spd": "avg_speed",
        "speed": "avg_speed",
        "avg_spd": "avg_speed",
        "avg_speed": "avg_speed",
        "cp_speed": "cp_speed",
        "cp_spd": "cp_speed",
        "allowed_cp_speed": "cp_speed",
        "rpm": "rpm",
        "main_engine_rpm": "rpm",
        "slip": "slip_pct",
        "slip_%": "slip_pct",
        "average_slip_pct": "slip_pct",
        "wind": "wind_speed",
        "wind_spd": "wind_speed",
        "wind_speed": "wind_speed",
        "bf": "beaufort",
        "beaufort": "beaufort",
        "buefort_scale": "beaufort",
        "remarks": "remarks",
        "other_remarks_if_any": "remarks",
        "me_cons": "me_lsfo",
        "me_lsfo": "me_lsfo",
        "me_lsfo_consumption": "me_lsfo",
        "ae_cons": "ae_lsfo",
        "ae_lsfo": "ae_lsfo",
        "ae_lsfo_consumption": "ae_lsfo",
        "boiler_cons": "boiler_lsfo",
        "boiler_lsfo": "boiler_lsfo",
        "boiler_lsfo_consumption": "boiler_lsfo",
        "total_lsfo": "total_lsfo",
        "total_lsfo_consumption": "total_lsfo",
        "mgo_cons": "total_mgo",
        "total_mgo": "total_mgo",
        "total_mgo_consumption": "total_mgo"
    }
    
    df.rename(columns=column_mapping, inplace=True)
    
    if "date" in df.columns:
        df = df.dropna(subset=["date"])
        # Remove template text or nans by checking all columns for 'example' or 'guideline'
        mask = df.astype(str).apply(lambda x: x.str.contains("example|guideline", case=False)).any(axis=1)
        df = df[~mask]
        # Also drop rows where date itself has 'nan'
        df = df[~df["date"].astype(str).str.contains("nan", case=False, na=False)]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        
    if "latitude" in df.columns:
        df = df.dropna(subset=["latitude"])
    
    numeric_cols = [
        "engine_distance", "avg_speed", "cp_speed", "rpm", "slip_pct", 
        "wind_speed", "beaufort", "me_lsfo", "ae_lsfo", "boiler_lsfo", 
        "total_lsfo", "total_mgo"
    ]
    
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            
    if "operation" in df.columns:
        df["operation"] = df["operation"].astype(str).str.title().str.strip()
    else:
        df["operation"] = "Unknown"
        
    if "remarks" not in df.columns:
        df["remarks"] = ""
    else:
        df["remarks"] = df["remarks"].fillna("").astype(str)
        
    return df