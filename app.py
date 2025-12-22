import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import numpy as np
import io
from src.model import ChargingStationModel

st.set_page_config(layout="wide", page_title="SIRQ Scientific Workbench")

# --- HELPER: VISUALIZATION RENDERER (For Page 1) ---
def render_station_visual(model):
    chargers = [a for a in model.schedule.agents if a.status == "Charging"]
    queue = [a for a in model.schedule.agents if a.status == "Queuing"]
    
    if model.strategy == "FIFO": queue.sort(key=lambda x: x.unique_id)
    else: queue.sort(key=lambda x: x.bid, reverse=True)

    charger_html = ""
    for i in range(model.num_chargers):
        if i < len(chargers):
            truck = chargers[i]
            charger_html += f"""<div style="background-color: {truck.color}; color: white; padding: 6px; border-radius: 6px; width: 90px; text-align: center; border: {truck.border}; margin: 3px; box-shadow: 1px 1px 3px rgba(0,0,0,0.2);"><div style="font-size: 14px; font-weight: bold;">⚡ {i+1}</div><div style="font-size: 12px; font-weight: bold;">${int(truck.bid)}</div><div style="font-size: 9px; opacity: 0.9;">{truck.profile_type[0]}</div></div>"""
        else:
            charger_html += f"""<div style="background-color: #f0f2f6; color: #bcccdb; padding: 6px; border-radius: 6px; width: 90px; text-align: center; border: 2px dashed #dbe4eb; margin: 3px;"><div style="font-size: 14px;">💤 {i+1}</div></div>"""
    queue_html = ""
    if not queue: queue_html = "<div style='color: #aaa; font-style: italic; font-size: 12px; padding: 5px;'>Queue is Empty</div>"
    else:
        for truck in queue[:12]:
            queue_html += f"""<div style="background-color: {truck.color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-align: center; margin: 2px; min-width: 45px; border: {truck.border};" title="ID: {truck.unique_id} | {truck.profile_type}"><div style="font-weight: bold;">${int(truck.bid)}</div></div>"""
        if len(queue) > 12: queue_html += f"<div style='color: #888; font-size: 10px;'>+{len(queue)-12} more</div>"

    return f"""<div style="font-family: sans-serif;"><div style="display: flex; flex-wrap: wrap; margin-bottom: 5px;">{charger_html}</div><div style="background-color: #f8f9fa; padding: 8px; border-radius: 8px; border-left: 4px solid #ddd; display: flex; flex-wrap: wrap;">{queue_html}</div></div>""".replace("\n", "").strip()

# --- SESSION STATE ---
if 'monte_carlo_df' not in st.session_state: 
    st.session_state['monte_carlo_df'] = None # Stores the Big Dataset

# --- SIDEBAR NAV ---
st.sidebar.title("🔬 SIRQ Workbench")
page = st.sidebar.radio("Workflow Step", [
    "1. Concept Demo (Visual)", 
    "2. Run Monte Carlo (Execution)", 
    "3. Deep Dive Analytics (Results)", 
    "4. Data Manager (Import/Export)"
])

# =========================================================
# PAGE 1: CONCEPT DEMO (The "Explanation" Layer)
# =========================================================
if page == "1. Concept Demo (Visual)":
    st.title("💡 Concept Validation")
    st.markdown("""
    **Objective:** Visual validation of the auction mechanism before large-scale testing.
    Use this page to verify that the queue logic (FIFO vs SIRQ) behaves as expected on a micro-scale.
    """)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.info("Configuration")
        strat = st.selectbox("Strategy", ["FIFO", "SIRQ"])
        load = st.selectbox("Traffic Load", [0.8, 1.0, 1.2, 1.5], index=1)
        speed = st.select_slider("Speed", ["Fast", "Normal", "Slow"], value="Fast")
        if st.button("▶️ Run Visual Demo"):
            # Run Logic
            model = ChargingStationModel(4, strategy=strat, seed=42, user_config={"traffic_multiplier": load})
            
            ph_vis = st.empty()
            ph_stats = st.empty()
            bar = st.progress(0)
            
            sleeps = {"Fast": 0.01, "Normal": 0.05, "Slow": 0.2}
            steps_skip = {"Fast": 10, "Normal": 5, "Slow": 1}
            
            for i in range(1440):
                model.step()
                if i % steps_skip[speed] == 0:
                    bar.progress((i+1)/1440)
                    ph_vis.markdown(render_station_visual(model), unsafe_allow_html=True)
                    ph_stats.caption(f"Time: {i//60}:00 | Rev: ${int(model.kpi_revenue)} | Failures: {model.kpi_failed_critical}")
                    time.sleep(sleeps[speed])
            st.success("Demo Complete. If logic holds, proceed to 'Run Monte Carlo'.")

# =========================================================
# PAGE 2: MONTE CARLO EXECUTION (The "Lab" Layer)
# =========================================================
elif page == "2. Run Monte Carlo (Execution)":
    st.title("⚡ Monte Carlo Experimentation")
    st.markdown("""
    **Objective:** Generate statistical significance by running $N$ simulations per configuration.
    This process runs in the background and populates the **Deep Dive Analytics** tab.
    """)
    
    with st.form("mc_config"):
        c1, c2, c3 = st.columns(3)
        with c1:
            n_runs = st.number_input("Iterations (N)", 30, 200, 50, help="N >= 30 required for Central Limit Theorem.")
            chargers = st.number_input("Chargers", 2, 8, 4)
        with c2:
            loads = st.multiselect("Traffic Multipliers", [0.5, 0.8, 1.0, 1.2, 1.5, 2.0], default=[0.8, 1.0, 1.2, 1.5])
            strats = st.multiselect("Strategies", ["FIFO", "SIRQ"], default=["FIFO", "SIRQ"])
        with c3:
            st.markdown("Profile Mix:")
            pc = st.slider("Critical %", 0, 100, 20)/100
            ps = st.slider("Standard %", 0, 100, 60)/100
            pe = st.slider("Economy %", 0, 100, 20)/100
        
        start_btn = st.form_submit_button("🚀 Start Simulation Batch")

    if start_btn:
        results = []
        progress = st.progress(0)
        status = st.empty()
        
        total_ops = len(loads) * len(strats) * n_runs
        completed = 0
        
        base_conf = {"prob_critical": pc, "prob_standard": ps, "prob_economy": pe}
        
        start_t = time.time()
        
        # --- BATCH LOOP ---
        for l in loads:
            for s in strats:
                for i in range(n_runs):
                    # Unique Seed
                    seed = np.random.randint(100000, 999999)
                    run_conf = base_conf.copy()
                    run_conf["traffic_multiplier"] = l
                    
                    model = ChargingStationModel(chargers, strategy=s, seed=seed, user_config=run_conf)
                    for _ in range(1440): model.step()
                    
                    # Extract Metrics
                    ag_df = pd.DataFrame(model.agent_log)
                    
                    # Safety check for empty logs
                    if not ag_df.empty:
                        crit_wait = ag_df.query("Profile=='CRITICAL'")['Wait_Time'].mean()
                        eco_wait = ag_df.query("Profile=='ECONOMY'")['Wait_Time'].mean()
                    else:
                        crit_wait, eco_wait = 0, 0
                        
                    results.append({
                        "Run_ID": i,
                        "Traffic_Load": l,
                        "Strategy": s,
                        "Revenue": model.kpi_revenue,
                        "Critical_Failures": model.kpi_failed_critical,
                        "Avg_Wait_Critical": crit_wait,
                        "Avg_Wait_Economy": eco_wait,
                        "Preemptions": model.kpi_preemptions
                    })
                    
                    completed += 1
                    if completed % 10 == 0:
                        progress.progress(completed / total_ops)
                        status.text(f"Simulating... {completed}/{total_ops}")
        
        # --- FINISH ---
        st.session_state['monte_carlo_df'] = pd.DataFrame(results)
        st.success(f"✅ Batch Complete! {total_ops} runs in {time.time()-start_t:.1f}s.")
        st.info("👉 Go to **'3. Deep Dive Analytics'** to inspect the results.")

# =========================================================
# PAGE 3: DEEP DIVE ANALYTICS (The "Paper" Layer)
# =========================================================
elif page == "3. Deep Dive Analytics (Results)":
    st.title("📊 Scientific Deep Dive")
    
    df = st.session_state['monte_carlo_df']
    
    if df is None:
        st.warning("⚠️ No Monte Carlo data found.")
        st.markdown("Please either **Run Monte Carlo** (Page 2) or **Import Data** (Page 4).")
    else:
        st.caption(f"Dataset Loaded: {len(df)} Simulations")
        
        # --- TABS FOR RQs ---
        tab1, tab2, tab3, tab4 = st.tabs([
            "RQ1: Economic Efficiency", 
            "RQ2: Critical Reliability", 
            "RQ3: Equity Analysis",
            "RQ4: Operational Robustness"
        ])
        
        # RQ1: REVENUE (Confidence Intervals)
        with tab1:
            st.markdown("### RQ1: Does SIRQ generate statistically significant revenue gains?")
            
            # Calculate 95% CI
            agg = df.groupby(["Traffic_Load", "Strategy"])["Revenue"].agg(["mean", "std", "count"]).reset_index()
            agg['ci'] = 1.96 * (agg['std'] / np.sqrt(agg['count']))
            
            fig = go.Figure()
            for s in df["Strategy"].unique():
                sub = agg[agg["Strategy"] == s]
                fig.add_trace(go.Scatter(
                    x=sub["Traffic_Load"], y=sub["mean"],
                    error_y=dict(type='data', array=sub['ci'], visible=True),
                    mode='lines+markers', name=s
                ))
            fig.update_layout(title="Mean Revenue vs Traffic Load (95% CI)", xaxis_title="Traffic Load", yaxis_title="Revenue ($)")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**Interpretation:** If error bars do not overlap, the revenue difference is scientifically significant.")

        # RQ2: CRITICAL WAIT TIMES (Box Plots)
        with tab2:
            st.markdown("### RQ2: Does SIRQ protect Critical Supply Chains?")
            fig = px.box(df, x="Traffic_Load", y="Avg_Wait_Critical", color="Strategy",
                         title="Distribution of Critical Truck Wait Times",
                         labels={"Avg_Wait_Critical": "Avg Wait Time (min)"})
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**Interpretation:** SIRQ should keep this metric near zero, even at high loads.")

        # RQ3: EQUITY (Scatter/Comparison)
        with tab3:
            st.markdown("### RQ3: The Cost of Priority (Equity)")
            st.markdown("Comparing the 'Pain' (Wait Time) felt by Economy trucks vs the 'Gain' by Critical trucks.")
            
            # Melt for side-by-side comparison
            melted = df.melt(id_vars=["Traffic_Load", "Strategy"], 
                             value_vars=["Avg_Wait_Critical", "Avg_Wait_Economy"], 
                             var_name="Profile", value_name="Wait_Time")
            
            fig = px.box(melted, x="Traffic_Load", y="Wait_Time", color="Profile", facet_col="Strategy",
                         title="Equity Gap: Critical vs Economy Wait Times")
            st.plotly_chart(fig, use_container_width=True)

        # RQ4: FAILURES (Robustness)
        with tab4:
            st.markdown("### RQ4: System Collapse Point")
            fig = px.line(df.groupby(["Traffic_Load", "Strategy"])["Critical_Failures"].mean().reset_index(),
                          x="Traffic_Load", y="Critical_Failures", color="Strategy", markers=True,
                          title="Avg Critical Failures (Impatient/Left)")
            st.plotly_chart(fig, use_container_width=True)

# =========================================================
# PAGE 4: DATA MANAGER (Import/Export)
# =========================================================
elif page == "4. Data Manager (Import/Export)":
    st.title("💾 Data Manager")
    st.markdown("Save your experiment for reproducibility or load a previous dataset for analysis.")
    
    col1, col2 = st.columns(2)
    
    # EXPORT
    with col1:
        st.subheader("📤 Export Current Data")
        if st.session_state['monte_carlo_df'] is not None:
            csv = st.session_state['monte_carlo_df'].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Monte Carlo Results (.csv)",
                data=csv,
                file_name="sirq_monte_carlo_results.csv",
                mime="text/csv"
            )
            st.success("Data ready for download.")
        else:
            st.info("No simulation data in memory to export.")
            
    # IMPORT
    with col2:
        st.subheader("📥 Import Dataset")
        uploaded_file = st.file_uploader("Upload 'sirq_monte_carlo_results.csv'", type="csv")
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                # Basic validation
                required_cols = ["Traffic_Load", "Strategy", "Revenue"]
                if all(col in df.columns for col in required_cols):
                    st.session_state['monte_carlo_df'] = df
                    st.success("✅ Dataset Imported Successfully!")
                    st.markdown("Go to **'3. Deep Dive Analytics'** to view the graphs.")
                else:
                    st.error("Invalid CSV format. Missing columns.")
            except Exception as e:
                st.error(f"Error reading file: {e}")