import pandas as pd

def evaluate(row, cleaning_bays=1):
    reasons, warnings = [], []
    for col, label in [
        ("fitness_mechanical", "Mechanical"),
        ("fitness_electrical", "Electrical"),
        ("fitness_signalling", "Signalling")
    ]:
        if not bool(row[col]):
            reasons.append(f"Invalid/expired {label} fitness certificate")
    if bool(row["critical_job_open"]):
        reasons.append("Critical open job card")
    if float(row["availability_pct"]) < 60:
        reasons.append("Availability below illustrative 60% threshold")
    if float(row["maintenance_health_pct"]) < 45:
        reasons.append("Maintenance health below illustrative 45% threshold")
    if float(row["energy_ready_pct"]) < 55:
        reasons.append("Energy readiness below illustrative 55% threshold")
    if int(row["blockers_ahead"]) > 0:
        warnings.append(f'{int(row["blockers_ahead"])} train(s) blocking exit; shunting required')
    if bool(row["cleaning_required"]) and not bool(row["cleaning_done"]):
        if cleaning_bays <= 0:
            reasons.append("Mandatory cleaning pending and no bay available")
        else:
            warnings.append("Cleaning must be completed in an allocated bay before departure")
    if bool(row["minor_job_open"]):
        warnings.append("Minor job card open; authorized deferral must be confirmed")
    required = float(row["sponsor_required_hours"])
    completed = float(row["sponsor_completed_hours"])
    remaining = max(0.0, required-completed)
    if str(row["sponsor"]).strip() and remaining:
        warnings.append(f"Sponsor visibility remaining: {remaining:.1f} hours")
    mileage_score = 100-min(100, float(row["total_km"])/500000*100)
    recent_score = 100-min(100, float(row["last_7d_km"])/2500*100)
    sponsor_score = 100 if not str(row["sponsor"]).strip() else min(100, completed/max(required,1)*100)
    score = round(.25*float(row["availability_pct"]) + .20*float(row["maintenance_health_pct"]) +
                  .15*float(row["energy_ready_pct"]) + .15*mileage_score +
                  .10*recent_score + .15*sponsor_score, 1)
    eligible = not reasons
    status = "NOT ELIGIBLE" if not eligible else (
        "ELIGIBLE AFTER CLEANING" if bool(row["cleaning_required"]) and not bool(row["cleaning_done"]) else "ELIGIBLE")
    return {"eligible": eligible, "status": status, "score": score,
            "block_reasons": reasons, "warnings": warnings,
            "sponsor_remaining_hours": round(remaining,1),
            "shunting_moves": int(row["blockers_ahead"])}

def build_plan(fleet, demand=10, cleaning_bays=1):
    rows=[]
    for _, row in fleet.iterrows():
        item=row.to_dict()
        item.update(evaluate(row, cleaning_bays))
        rows.append(item)
    plan=pd.DataFrame(rows).sort_values(["eligible","score","total_km"], ascending=[False,False,True])
    selected=[]
    bays=int(cleaning_bays)
    for _, row in plan.iterrows():
        if len(selected)>=int(demand): break
        if not row["eligible"]: continue
        if row["status"]=="ELIGIBLE AFTER CLEANING":
            if bays<=0: continue
            bays-=1
        selected.append(row["train_id"])
    plan["inducted"]=plan["train_id"].isin(selected)
    plan["decision"]=plan["inducted"].map({True:"INDUCT",False:"HOLD"})
    plan.loc[(~plan["inducted"]) & plan["eligible"],"decision"]="RESERVE / NOT SELECTED"
    return plan
