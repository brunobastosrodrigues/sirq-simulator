import streamlit as st
import pandas as pd
import numpy as np
import time
from src.model import ChargingStationModel
from src.vis_utils import render_station_visual
from src.analytics import ScientificPlotter

st.set_page_config(layout="wide", page_title="SIRQ Research Workbench")

# --- SIDEBAR & SETUP ---
if 'monte_carlo_df' not in st.session_state: st.session_state['monte_carlo_df'] = None

st.sidebar.title("🔬 SIRQ Workbench")
page = st.sidebar.radio("Workflow", [
    "1. Concept Demo (Explainability)", 
    "2. Monte Carlo (Execution)", 
    "3. Deep Dive Analytics (Results)", 
    "4. Data Manager"
])

# =========================================================
# PAGE 1: CONCEPT DEMO (PARALLEL & EXPLAINABLE)
# =========================================================
if page == "1. Concept Demo (Explainability)":
    st.title("💡 Concept Validation")
    
    # Explainability Section
    st.markdown("""
    ### What are we observing?
    This is a **Digital Twin** comparison of two queueing strategies.
    
    * **🔴 Critical Trucks (Red):** High urgency, high willingness to pay. We want these processed *fast*.
    * **🔵 Standard Trucks (Blue):** Normal operations.
    * **⚪ Economy Trucks (Gray):** Price sensitive, can wait.
    
    **Hypothesis:** SIRQ (Right) will allow Red trucks to "jump" the queue, while FIFO (Left) will block them behind Gray trucks.
    """)
    
    # Config
    c1, c2, c3 = st.columns(3)
    with c1: load = st.selectbox("Traffic Load", [0.8, 1.0, 1.2, 1.5], index=1)
    with c2: speed = st.select_slider("Speed", ["Normal", "Fast"], value="Fast")
    with c3: st.write(""); st.write(""); start_btn = st.button("▶️ Run Parallel Simulation", type="primary")
    
    if start_btn:
        # Init Parallel Models
        cfg = {"traffic_multiplier": load}
        fifo = ChargingStationModel(4, "FIFO", seed=42, user_config=cfg)
        sirq = ChargingStationModel(4, "SIRQ", seed=42, user_config=cfg)
        
        # Layout
        c_fifo, c_sirq = st.columns(2)
        with c_fifo: 
            st.subheader("🔵 FIFO (First-In-First-Out)")
            st.caption("Traditional approach. Note how Red trucks get stuck.")
            ph_fifo = st.empty()
            stat_fifo = st.empty()
        with c_sirq: 
            st.subheader("🟢 SIRQ (Auction-Based)")
            st.caption("Our proposal. Note Red trucks moving to chargers.")
            ph_sirq = st.empty()
            stat_sirq = st.empty()
            
        bar = st.progress(0)
        
        # Parallel Loop
        skip = 5 if speed == "Normal" else 20
        sleep = 0.05 if speed == "Normal" else 0.001
        
        for i in range(1440):
            fifo.step()
            sirq.step()
            
            if i % skip == 0:
                bar.progress((i+1)/1440)
                # Render Both Side-by-Side
                ph_fifo.markdown(render_station_visual(fifo), unsafe_allow_html=True)
                stat_fifo.info(f"Rev: ${int(fifo.kpi_revenue)} | Fail: {fifo.kpi_failed_critical}")
                
                ph_sirq.markdown(render_station_visual(sirq), unsafe_allow_html=True)
                stat_sirq.success(f"Rev: ${int(sirq.kpi_revenue)} | Fail: {sirq.kpi_failed_critical}")
                
                time.sleep(sleep)

# =========================================================
# PAGE 2: MONTE CARLO EXECUTION
# =========================================================
elif page == "2. Monte Carlo (Execution)":
    st.title("⚡ Monte Carlo Experiment")
    st.markdown("Run $N$ simulations to generate the dataset for the Deep Dive Analytics.")
    
    with st.form("mc_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_runs = st.number_input("N (Runs per Config)", 30, 200, 50)
            loads = st.multiselect("Traffic Loads", [0.5, 0.8, 1.0, 1.2, 1.5, 2.0], default=[0.8, 1.0, 1.2, 1.5])
        with c2:
            st.markdown("Profile Mix (Must sum to 1.0):")
            pc = st.slider("Critical %", 0.0, 1.0, 0.2)
            ps = st.slider("Standard %", 0.0, 1.0, 0.6)
            pe = st.slider("Economy %", 0.0, 1.0, 0.2)
        
        run_btn = st.form_submit_button("🚀 Execute Batch")
        
    if run_btn:
        results = []
        progress = st.progress(0)
        status = st.empty()
        total_steps = len(loads) * 2 * n_runs # 2 strategies
        curr = 0
        
        base_cfg = {"prob_critical": pc, "prob_standard": ps, "prob_economy": pe}
        
        for l in loads:
            for s in ["FIFO", "SIRQ"]:
                for i in range(n_runs):
                    seed = np.random.randint(100000, 999999)
                    cfg = base_cfg.copy()
                    cfg["traffic_multiplier"] = l
                    
                    m = ChargingStationModel(4, s, seed=seed, user_config=cfg)
                    for _ in range(1440): m.step()
                    
                    # Extract Data
                    log = pd.DataFrame(m.agent_log)
                    if not log.empty:
                        crit_w = log.query("Profile=='CRITICAL'")['Wait_Time'].mean()
                        eco_w = log.query("Profile=='ECONOMY'")['Wait_Time'].mean()
                    else:
                        crit_w, eco_w = 0, 0
                        
                    results.append({
                        "Run_ID": i, "Traffic_Load": l, "Strategy": s,
                        "Revenue": m.kpi_revenue, "Critical_Failures": m.kpi_failed_critical,
                        "Avg_Wait_Critical": crit_w, "Avg_Wait_Economy": eco_w
                    })
                    curr += 1
                    if curr % 10 == 0:
                        progress.progress(curr/total_steps)
                        status.text(f"Simulating {curr}/{total_steps}...")
                        
        st.session_state['monte_carlo_df'] = pd.DataFrame(results)
        st.success("Batch Complete. Proceed to Deep Dive Analytics.")

# =========================================================
# PAGE 3: DEEP DIVE ANALYTICS (MODULAR & EXPANDABLE)
# =========================================================
elif page == "3. Deep Dive Analytics (Results)":
    st.title("📊 Scientific Deep Dive")
    
    df = st.session_state['monte_carlo_df']
    if df is None:
        st.warning("No Data. Please run Monte Carlo or Import Data.")
    else:
        st.caption(f"Analyzing {len(df)} Simulations.")
        plotter = ScientificPlotter(df)
        
        tab1, tab2, tab3 = st.tabs(["RQ1: Efficiency", "RQ2: Critical Priority", "RQ3: Equity"])
        
        # --- RQ1: REVENUE ---
        with tab1:
            st.header("RQ1: Economic Efficiency")
            st.markdown("*Does SIRQ generate higher revenue significantly?*")
            
            # Primary Plot
            st.plotly_chart(plotter.rq1_revenue_ci(), use_container_width=True)
            
            # Expandable Details
            with st.expander("🔎 Drill Down: Distributions & Deltas"):
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plotter.rq1_revenue_dist(), use_container_width=True)
                with c2: 
                    delta_fig = plotter.rq1_revenue_delta()
                    if delta_fig: st.plotly_chart(delta_fig, use_container_width=True)
                    else: st.info("Need both FIFO and SIRQ data for Delta analysis.")

        # --- RQ2: CRITICAL PRIORITY ---
        with tab2:
            st.header("RQ2: Service Level Agreement")
            st.markdown("*Does SIRQ protect critical agents under stress?*")
            
            # Primary Plot
            st.plotly_chart(plotter.rq2_critical_wait_box(), use_container_width=True)
            
            # Expandable Details
            with st.expander("🔎 Drill Down: Failures & Probability (ECDF)"):
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plotter.rq2_failure_rate(), use_container_width=True)
                with c2: 
                    st.markdown("**ECDF (Empirical Cumulative Distribution Function)**")
                    st.caption("Shows the probability that a truck waits less than X minutes.")
                    st.plotly_chart(plotter.rq2_ecdf_wait(), use_container_width=True)

        # --- RQ3: EQUITY ---
        with tab3:
            st.header("RQ3: Equity Analysis")
            st.markdown("*What is the cost imposed on non-critical agents?*")
            
            # Primary Plot
            st.plotly_chart(plotter.rq3_equity_gap(), use_container_width=True)
            
            with st.expander("🔎 Drill Down: Starvation Scatter"):
                st.markdown("Each dot is a single simulation run. Look for dots high on Y-axis (Economy suffering).")
                st.plotly_chart(plotter.rq3_starvation_scatter(), use_container_width=True)

# =========================================================
# PAGE 4: DATA MANAGER
# =========================================================
elif page == "4. Data Manager":
    st.title("💾 Data Manager")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Export")
        if st.session_state['monte_carlo_df'] is not None:
            csv = st.session_state['monte_carlo_df'].to_csv(index=False).encode('utf-8')
            st.download_button("Download Dataset (.csv)", csv, "sirq_dataset.csv", "text/csv")
    
    with c2:
        st.subheader("Import")
        f = st.file_uploader("Upload CSV", type="csv")
        if f:
            st.session_state['monte_carlo_df'] = pd.read_csv(f)
            st.success("Loaded! Go to Deep Dive Analytics.")