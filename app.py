"""Streamlit UI for the Agentic RFP Evaluation and Supplier Ranking project."""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from rfp_agents.orchestrator import run_evaluation
from database.database import get_run, initialize_database, list_criteria, list_runs, seed_criteria, update_criteria

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

st.set_page_config(page_title="ProcureIQ | RFP Evaluator", page_icon="◈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f5f7fb; color: #14263d; }
h1,h2,h3,h4 { font-family: 'Manrope', sans-serif; color: #14263d; letter-spacing: -0.025em; }
.hero { padding: 26px 30px; border-radius: 18px; background: linear-gradient(120deg,#10263f 0%,#164e63 62%,#0e7490 100%); color: white; margin: 4px 0 20px; box-shadow: 0 12px 30px #17324d20; }
.hero h1 { color: white; margin: 0; font-size: 2rem; }
.hero p { color: #d9eaf0; margin: 7px 0 0; font-size: 1rem; }
.eyebrow { color: #67e8f9; font-weight: 700; text-transform: uppercase; letter-spacing: .12em; font-size: .73rem; margin-bottom: 8px; }
.metric-card { background: white; border: 1px solid #e4eaf1; border-radius: 14px; padding: 16px 18px; box-shadow: 0 3px 12px #14263d08; }
.workflow-step { color: #14263d; }
.metric-label { color: #64748b; font-size: .78rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }
.metric-value { color: #14263d; font-size: 1.45rem; font-weight: 800; margin-top: 5px; font-family: 'Manrope',sans-serif; }
.section-note { color: #64748b; margin-top: -10px; margin-bottom: 14px; }
.rank-pill { background: #e0f2fe; color: #075985; border-radius: 999px; padding: 4px 11px; font-weight: 700; }
.stButton>button[kind="primary"] { background: #0e7490; border: 0; border-radius: 9px; font-weight: 700; }
[data-testid="stSidebar"] { background: #10263f; }
[data-testid="stSidebar"] * { color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)


def initialize() -> None:
    initialize_database()
    seed_criteria()


try:
    initialize()
except Exception as exc:
    st.error(f"Database initialization failed: {exc}")
    st.stop()


def metric(label: str, value: str) -> None:
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)


def criteria_page() -> None:
    st.header("Evaluation criteria")
    st.markdown('<p class="section-note">Criteria are loaded from SQLite. Active weights must total exactly 100% before a run can start.</p>', unsafe_allow_html=True)
    items = list_criteria()
    frame = pd.DataFrame(items)
    edited = st.data_editor(
        frame,
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        disabled=["criterion_id"],
        column_config={
            "criterion_id": st.column_config.NumberColumn("ID", width="small"),
            "name": st.column_config.TextColumn("Criterion", required=True, width="medium"),
            "description": st.column_config.TextColumn("What to assess", width="large"),
            "weight": st.column_config.NumberColumn("Weight %", min_value=0, max_value=100, step=1, format="%.1f"),
            "max_score": st.column_config.NumberColumn("Max score", min_value=0.1, max_value=100, step=0.5),
            "is_active": st.column_config.CheckboxColumn("Active"),
        },
        key="criteria_editor",
    )
    active = edited[edited["is_active"].astype(bool)]
    total = float(active["weight"].sum()) if not active.empty else 0.0
    left, right = st.columns([2, 5])
    with left:
        if abs(total - 100) < 1e-6:
            st.success(f"Active weights: {total:.1f}%")
        else:
            st.warning(f"Active weights: {total:.1f}% — adjust to exactly 100% to evaluate.")
    with right:
        if st.button("Save criteria", type="primary"):
            try:
                names = [str(x).strip().casefold() for x in edited["name"]]
                if any(not x for x in names) or len(set(names)) != len(names):
                    raise ValueError("Criterion names must be non-empty and unique.")
                if any(float(x) <= 0 for x in edited["max_score"]):
                    raise ValueError("Maximum scores must be greater than zero.")
                if any(float(x) < 0 for x in edited["weight"]):
                    raise ValueError("Weights cannot be negative.")
                update_criteria(edited.to_dict("records"))
                st.success("Criteria saved to SQLite.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save criteria: {exc}")
    with st.expander("How weights affect results"):
        st.write("Weights are used by deterministic Python for the absolute weighted score and Peer Performance Index. The prompt receives criterion names, descriptions, weights, and maximum scores dynamically from SQLite.")


def supplier_input_page() -> None:
    st.header("Supplier input")
    st.markdown('<p class="section-note">Upload multiple text-based RFP PDFs and provide consistent metadata for every supplier.</p>', unsafe_allow_html=True)
    active_run_id = st.session_state.get("active_run_id")
    if active_run_id:
        saved_run = get_run(active_run_id)
        if saved_run and saved_run.get("status") == "COMPLETED":
            show_run(saved_run)
            if st.button("Start a new evaluation batch"):
                del st.session_state["active_run_id"]
                st.rerun()
            return
    criteria = list_criteria(active_only=True)
    weight_sum = sum(float(c["weight"]) for c in criteria)
    if not criteria:
        st.error("No active criteria. Open Criteria and activate at least one criterion.")
    elif abs(weight_sum - 100) > 1e-6:
        st.warning(f"Active weights total {weight_sum:g}%. They must total 100% before an evaluation can run.")
    uploads = st.file_uploader("Supplier proposal PDFs", type=["pdf"], accept_multiple_files=True, help="Upload searchable PDFs. Image-only scans need OCR first.")
    metadata = []
    problems: list[str] = []
    if uploads:
        st.subheader(f"Supplier metadata · {len(uploads)} documents")
        for index, upload in enumerate(uploads):
            with st.container(border=True):
                st.markdown(f"**{index + 1}. {upload.name}** · {upload.size / 1024:.0f} KB")
                a, b, c = st.columns([2, 1, 1])
                default_name = Path(upload.name).stem.replace("_", " ").title()
                name = a.text_input("Supplier name", value=default_name, key=f"name_{index}_{upload.name}")
                submitted = b.date_input("Submission date", value=date.today(), key=f"date_{index}_{upload.name}")
                rating = c.number_input("Historical experience (0–10)", min_value=0.0, max_value=10.0, value=5.0, step=0.5, key=f"experience_{index}_{upload.name}")
                if not name.strip():
                    problems.append(f"{upload.name}: supplier name is required.")
                if submitted > date.today():
                    problems.append(f"{name or upload.name}: submission date cannot be in the future.")
                if upload.size == 0:
                    problems.append(f"{upload.name}: file is empty.")
                metadata.append({"supplier_name": name.strip(), "submission_date": submitted.isoformat(), "experience_rating": rating, "pdf_bytes": upload.getvalue()})
    if metadata:
        normalized_names = [m["supplier_name"].casefold() for m in metadata]
        if len(normalized_names) != len(set(normalized_names)):
            problems.append("Supplier names must be unique within a batch.")
    if problems:
        for problem in problems:
            st.error(problem)
    if uploads:
        st.info("With no LLM_API_KEY, the app uses deterministic DEMO mode. A configured OpenAI-compatible model uses the evidence-grounded Evaluation Agent. Both modes pass through the same validation, scoring, benchmarking, ranking, and persistence tools.")
    if st.button("Evaluate Suppliers", type="primary", disabled=not uploads or bool(problems) or not criteria or abs(weight_sum - 100) > 1e-6, width="stretch"):
        bar = st.progress(0, text="Preparing evaluation batch…")
        status = st.empty()
        stages = ["Extracting PDF", "Evaluating proposal", "Validating AI output", "Calculating scores and criterion benchmarks", "Ranking suppliers", "Saving results"]
        def on_progress(index: int, stage: str, detail: str) -> None:
            total_steps = max(1, len(metadata) * 3 + 3)
            if stage in stages[:3]:
                pct = min(0.58, (index * 3 + stages[:3].index(stage) + 1) / total_steps)
            else:
                pct = {"Calculating scores and criterion benchmarks": .68, "Ranking suppliers": .82, "Saving results": .94}.get(stage, .5)
            bar.progress(pct, text=f"{stage} · {detail}")
            status.caption("Workflow: " + " → ".join(stages))
        try:
            result = run_evaluation(metadata, criteria, on_progress)
            bar.progress(1.0, text=f"Complete · {result['rfp_run_id']}")
            st.session_state["active_run_id"] = result["rfp_run_id"]
            st.success(f"Evaluation complete. {len(result['suppliers'])} suppliers ranked · mode: {result['mode']}.")
            st.rerun()
        except Exception as exc:
            bar.empty()
            st.error(f"Evaluation failed cleanly: {exc}")


def show_run(run: dict) -> None:
    suppliers = run["suppliers"]
    mode = run.get("mode", "Stored")
    st.header("Supplier leaderboard")
    if mode == "DEMO":
        st.warning("DEMO MODE · deterministic synthetic scoring is active. No LLM API key was used.")
    elif mode in ("LLM", "MIXED"):
        st.success(f"Evaluation mode: {mode} · LLM judgments were normalized before deterministic scoring.")
    if suppliers:
        a, b, c, d = st.columns(4)
        with a: metric("Suppliers", str(len(suppliers)))
        with b: metric("Top PPI", f"{suppliers[0]['ppi']:.2f}%")
        with c: metric("Top absolute score", f"{suppliers[0]['absolute_score']:.2f}/100")
        with d: metric("Run status", run.get("status", "COMPLETED"))
        board = pd.DataFrame([{"Rank": s["final_rank"], "Supplier": s["supplier_name"], "Absolute score": round(s["absolute_score"], 2), "PPI": round(s["ppi"], 2), "Submission date": s["submission_date"], "Experience rating": s["experience_rating"]} for s in suppliers])
        st.dataframe(board, hide_index=True, width="stretch", column_config={"Rank": st.column_config.NumberColumn(format="%d"), "PPI": st.column_config.ProgressColumn("PPI", min_value=0, max_value=100, format="%.2f%%")})
        st.caption("Tie-break order: higher PPI → earlier submission date → higher historical experience rating → supplier name A–Z. Ranks are assigned after the complete stable sort.")
        st.subheader("Detailed scorecards")
        for supplier in suppliers:
            title = f"#{supplier['final_rank']} · {supplier['supplier_name']} — PPI {supplier['ppi']:.2f}%"
            with st.expander(title, expanded=(supplier["final_rank"] == 1)):
                x, y, z = st.columns(3)
                x.metric("Absolute score", f"{supplier['absolute_score']:.2f} / 100")
                y.metric("Submission date", supplier["submission_date"])
                z.metric("Experience rating", f"{supplier['experience_rating']:.1f} / 10")
                details = pd.DataFrame([{"Criterion": c["name"], "Score": c["score"], "Maximum": c["max_score"], "Weight %": next((cr["weight"] for cr in run["criteria"] if cr["criterion_id"] == c["criterion_id"]), 0), "Benchmark": c["benchmark"], "Gap": c["gap"], "Relative %": c["relative_performance_pct"], "Evidence": c["evidence"], "Justification": c["justification"]} for c in supplier["criteria"]])
                st.dataframe(details, hide_index=True, width="stretch", column_config={"Score": st.column_config.NumberColumn(format="%.2f"), "Relative %": st.column_config.NumberColumn(format="%.2f%%"), "Gap": st.column_config.NumberColumn(format="%.2f")})
                st.markdown("**Overall summary**")
                st.write(supplier["overall_summary"])
                st.markdown("**Risks**")
                if supplier["risks"]:
                    for risk in supplier["risks"]: st.markdown(f"- {risk}")
                else:
                    st.write("No risks were identified by the Evaluation Agent.")
                if supplier["warnings"]:
                    st.warning("Validation warnings\n\n" + "\n".join(f"- {warning}" for warning in supplier["warnings"]))
                else:
                    st.success("No validation warnings for this supplier.")
        st.subheader("Run details")
        x, y, z = st.columns(3)
        x.code(run["rfp_run_id"])
        y.write(f"Created: {run['created_at']}")
        z.write(f"Suppliers: {len(suppliers)} · Status: {run.get('status', 'COMPLETED')}")
        all_warnings = run.get("warnings", [])
        st.write(f"Validation warnings: **{len(all_warnings)}**")
        with st.expander("Tie-break rules and scoring policy"):
            for rule in run.get("tie_break_rules", []): st.markdown(f"- {rule}")
            st.write("PPI is the active-weighted average of each criterion's relative performance percentage. If a criterion benchmark is zero, every supplier receives a neutral 100% relative value for that criterion; no division by zero occurs.")
        st.download_button("Download complete result JSON", data=json.dumps(run, indent=2, ensure_ascii=False), file_name=f"{run['rfp_run_id']}.json", mime="application/json", type="primary")
    else:
        st.info("This run has no completed supplier results.")


st.sidebar.markdown("## ◈ ProcureIQ")
st.sidebar.caption("Agentic RFP evaluation workspace")
page = st.sidebar.radio("Workspace", ["Overview", "Evaluate suppliers", "Criteria", "Run history"], label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption("Evaluation Agent · Validation Tool · Deterministic Ranking Tool · SQLite")

if page == "Overview":
    st.markdown('<div class="hero"><div class="eyebrow">Agentic procurement intelligence</div><h1>RFP Evaluation Workspace</h1><p>Compare supplier proposals with evidence-grounded AI judgments and transparent, deterministic business rules.</p></div>', unsafe_allow_html=True)
    runs = list_runs()
    active = list_criteria(active_only=True)
    total_weight = sum(float(c["weight"]) for c in active)
    a, b, c, d = st.columns(4)
    with a: metric("Saved evaluation runs", str(len(runs)))
    with b: metric("Active criteria", str(len(active)))
    with c: metric("Active weights", f"{total_weight:.0f}%")
    with d: metric("Evaluation mode", "DEMO" if not os.getenv("LLM_API_KEY", "").strip() else os.getenv("LLM_MODEL", "LLM"))
    st.markdown("### Agentic workflow")
    phases = st.columns(6)
    for col, (n, label) in zip(phases, [("01", "Extract PDF"), ("02", "Evaluate"), ("03", "Validate"), ("04", "Score"), ("05", "Benchmark & rank"), ("06", "Persist & present")]):
        with col:
            st.markdown(f'<div class="metric-card"><div class="metric-label">STEP {n}</div><div class="workflow-step" style="font-weight:700;margin-top:8px">{label}</div></div>', unsafe_allow_html=True)
    st.markdown("### Get started")
    st.write("Open **Evaluate suppliers** to upload proposal PDFs. The four fictional proposals in `sample_rfps/` are ready for a demonstration run. Configure an OpenAI-compatible endpoint in `.env` to use live model evaluations; otherwise, the clearly marked deterministic demo evaluator is used.")
    if runs:
        chosen = st.session_state.get("active_run_id", runs[0]["rfp_run_id"])
        stored = get_run(chosen)
        if stored and stored["status"] == "COMPLETED":
            show_run(stored)
        else:
            st.info("Choose a completed evaluation from Run history to view its leaderboard.")
elif page == "Evaluate suppliers":
    st.markdown('<div class="hero"><div class="eyebrow">New batch</div><h1>Evaluate supplier proposals</h1><p>One run ID, one shared criteria snapshot, complete evidence and validation trace.</p></div>', unsafe_allow_html=True)
    supplier_input_page()
elif page == "Criteria":
    criteria_page()
else:
    st.header("Run history")
    runs = list_runs()
    if not runs:
        st.info("No evaluation runs have been saved yet.")
    else:
        st.dataframe(pd.DataFrame(runs).rename(columns={"rfp_run_id": "Run ID", "created_at": "Created", "status": "Status", "supplier_count": "Suppliers"}), hide_index=True, width="stretch")
        selected = st.selectbox("Open a run", [r["rfp_run_id"] for r in runs], index=0)
        run = get_run(selected)
        if run:
            if run["status"] != "COMPLETED":
                st.error(f"Run status: {run['status']} · {run.get('error_message') or 'No details available.'}")
            else:
                show_run(run)
