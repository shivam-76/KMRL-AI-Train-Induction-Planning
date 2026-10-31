import streamlit as st
import pandas as pd
import plotly.express as px
from modules.storage import load_fleet, save_fleet, validate
from modules.engine import build_plan

st.set_page_config(page_title="KMRL Train Induction Planner", page_icon="🚇", layout="wide")
st.title("🚇 AI-Driven Train Induction Planning & Scheduling")
st.caption("Kochi Metro Rail Limited | Academic decision-support prototype")
if "fleet" not in st.session_state: st.session_state.fleet=load_fleet()
with st.sidebar:
    st.header("Shift planning")
    demand=st.number_input("Trains required",1,25,10)
    bays=st.number_input("Cleaning bays available",0,10,2)
    st.info("Safety hard-stops are applied before ranking. Scores cannot override invalid certificates or critical repairs.")
    if st.button("Reload original demo data"):
        st.session_state.fleet=load_fleet()
        st.rerun()
fleet=st.session_state.fleet.copy()
plan=build_plan(fleet,int(demand),int(bays))
tabs=st.tabs(["Dashboard","Induction Plan","Fitness Certificates","Job Cards","Sponsor Branding","Mileage Balancing","Cleaning Scheduler","Parking & Shunting","AI Logic","Data Management"])
with tabs[0]:
    a,b,c,d=st.columns(4)
    a.metric("Total trains",len(plan)); b.metric("Eligible",int(plan.eligible.sum()))
    c.metric("Recommended",int(plan.inducted.sum())); d.metric("Held",int((~plan.eligible).sum()))
    x,y=st.columns(2)
    x.plotly_chart(px.pie(plan,names="decision",title="Induction decision split"),use_container_width=True)
    y.plotly_chart(px.bar(plan,x="train_id",y="score",color="decision",title="Readiness score"),use_container_width=True)
    st.warning("Synthetic demo data and illustrative thresholds only. Not approved for real train dispatch.")
with tabs[1]:
    cols=["train_id","decision","status","score","sponsor_remaining_hours","shunting_moves","block_reasons","warnings"]
    st.dataframe(plan[cols],use_container_width=True,hide_index=True)
    st.download_button("Download induction plan CSV",plan[cols].to_csv(index=False).encode(),"induction_plan.csv","text/csv")
    if int(plan.inducted.sum())<demand: st.warning("Current constraints allow fewer trains than requested. Safety gates have not been relaxed.")
with tabs[2]:
    cols=["train_id","fitness_mechanical","fitness_electrical","fitness_signalling"]
    v=fleet[cols].copy(); v["all_certificates_valid"]=v[cols[1:]].all(axis=1)
    st.dataframe(v,use_container_width=True,hide_index=True)
    st.caption("Any invalid certificate is a hard stop.")
with tabs[3]:
    st.dataframe(fleet[["train_id","critical_job_open","minor_job_open","maintenance_health_pct"]],use_container_width=True,hide_index=True)
    st.info("Critical open job blocks operation. Minor job is flagged for authorized policy review.")
with tabs[4]:
    s=fleet[["train_id","sponsor","sponsor_required_hours","sponsor_completed_hours"]].copy()
    s["remaining_hours"]=(s.sponsor_required_hours-s.sponsor_completed_hours).clip(lower=0)
    st.dataframe(s,use_container_width=True,hide_index=True)
    st.metric("Sponsor visibility remaining",f'{s.remaining_hours.sum():.1f} hours')
with tabs[5]:
    st.plotly_chart(px.bar(fleet.sort_values("total_km"),x="train_id",y="total_km",title="Cumulative mileage"),use_container_width=True)
    st.plotly_chart(px.bar(fleet,x="train_id",y="last_7d_km",title="Mileage in last 7 days"),use_container_width=True)
with tabs[6]:
    pending=fleet[fleet.cleaning_required & ~fleet.cleaning_done]
    st.metric("Cleaning bays available",int(bays))
    st.write("Trains requiring deep cleaning")
    st.dataframe(pending[["train_id","cleaning_required","cleaning_done"]],use_container_width=True,hide_index=True)
    if len(pending)>bays: st.warning("Pending cleaning exceeds available bay count.")
with tabs[7]:
    p=fleet[["train_id","parking_row","parking_position","blockers_ahead"]].copy()
    p["movement_note"]=p.apply(lambda r:f'{int(r.blockers_ahead)} blocker(s) must move before exit' if r.blockers_ahead else "Exit path clear",axis=1)
    st.dataframe(p,use_container_width=True,hide_index=True)
    st.caption("Shunting estimate is simplified from blocker count; actual depot topology is not modeled.")
with tabs[8]:
    st.write("Rule-based decision support ranks only trains that pass mandatory hard constraints.")
    st.code("Score = 0.25×Availability + 0.20×Maintenance + 0.15×Energy + 0.15×Mileage balance + 0.10×Recent mileage balance + 0.15×Sponsor progress")
    st.dataframe(plan[["train_id","eligible","score","decision","block_reasons","warnings"]],use_container_width=True,hide_index=True)
    st.caption("This is a transparent heuristic, not a validated predictive ML model.")
with tabs[9]:
    st.subheader("Upload fleet data")
    st.write("Upload a CSV with the same columns as data/fleet.csv. Download the template below.")
    st.download_button("Download CSV template",fleet.head(0).to_csv(index=False).encode(),"fleet_template.csv","text/csv")
    uploaded=st.file_uploader("Choose fleet CSV file",type=["csv"])
    if uploaded is not None:
        try:
            incoming=pd.read_csv(uploaded)
            errors=validate(incoming)
            if errors:
                for err in errors: st.error(err)
            else:
                st.success(f"CSV validated: {len(incoming)} train records.")
                if st.button("Apply uploaded data"):
                    save_fleet(incoming)
                    st.session_state.fleet=incoming.copy()
                    st.success("Data saved successfully.")
                    st.rerun()
        except Exception as e: st.error(f"Could not read CSV: {e}")
    st.divider()
    st.subheader("Edit current fleet")
    edited=st.data_editor(st.session_state.fleet,num_rows="fixed",use_container_width=True)
    if st.button("Validate and save edited data"):
        errors=validate(edited)
        if errors:
            for err in errors: st.error(err)
        else:
            save_fleet(edited); st.session_state.fleet=edited.copy()
            st.success("Fleet data saved to data/fleet.csv")
            st.rerun()
    st.download_button("Download current fleet CSV",st.session_state.fleet.to_csv(index=False).encode(),"fleet.csv","text/csv")
