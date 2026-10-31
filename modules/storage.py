from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
FLEET_FILE=ROOT/"data"/"fleet.csv"
REQUIRED=["train_id","fitness_mechanical","fitness_electrical","fitness_signalling",
"critical_job_open","minor_job_open","sponsor","sponsor_required_hours","sponsor_completed_hours",
"total_km","last_7d_km","cleaning_required","cleaning_done","parking_row","parking_position",
"blockers_ahead","energy_ready_pct","availability_pct","maintenance_health_pct"]
def load_fleet(): return pd.read_csv(FLEET_FILE)
def save_fleet(df):
    errors=validate(df)
    if errors: raise ValueError("; ".join(errors))
    df[REQUIRED].to_csv(FLEET_FILE,index=False)
def validate(df):
    errors=[f"Missing columns: {', '.join(c for c in REQUIRED if c not in df.columns)}"] if any(c not in df.columns for c in REQUIRED) else []
    if errors: return errors
    if df["train_id"].astype(str).str.strip().eq("").any() or df["train_id"].astype(str).duplicated().any():
        errors.append("Train IDs must be non-empty and unique.")
    for c in ["total_km","last_7d_km","sponsor_required_hours","sponsor_completed_hours","parking_position","blockers_ahead","energy_ready_pct","availability_pct","maintenance_health_pct"]:
        v=pd.to_numeric(df[c],errors="coerce")
        if v.isna().any() or (v<0).any(): errors.append(f"{c} must contain non-negative numbers.")
    for c in ["energy_ready_pct","availability_pct","maintenance_health_pct"]:
        if not pd.to_numeric(df[c],errors="coerce").between(0,100).all(): errors.append(f"{c} must be between 0 and 100.")
    return errors
