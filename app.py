import streamlit as st
import pandas as pd
import numpy as np
import time
import os
from src.model import ChargingStationModel
from src.vis_utils import render_station_visual
from src.analytics import ScientificPlotter

st.set_page_config(layout="wide", page_title="SIRQ Simulator", page_icon="⚡")

# --- CUSTOM CSS FOR MODERN LOOK ---
st.markdown("""
<style>
    .big-font { font-size: 20px !important; color: #555; }
    .highlight { color: #2e86c1; font-weight: bold; }
    .concept-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #2e86c1; }
    .stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR & SETUP ---
if 'monte_carlo_df' not in st.session_state: st.session_state['monte_carlo_df'] = None

st.sidebar.header("⚡ SIRQ Platform")
page = st.sidebar.radio("Navigate", [
    "1. Concept & Demo", 
    "2. Scientific Simulation (Lab)", 
    "3. Deep Dive Analytics", 
    "4. Data Manager"
])

# =========================================================
# PAGE 1: CONCEPT & DEMO (The Educational Layer)
# =========================================================
if page == "1. Concept & Demo":
    
    # --- SECTION A: HEADER & CONCEPT ---
    st.title("SIRQ: System for Interactive Reservation and Queueing")
    st.markdown("##### *A Market-Based Approach to Electric Truck Charging*")
    
    st.divider()

    col_text, col_img = st.columns([1.2, 1])
    
    with col_text:
        st.markdown("""
        <div class="big-font">
        <b>SIRQ</b> proposes a paradigm shift in how we manage limited charging infrastructure.
        Instead of the traditional "First-Come-First-Served" (FIFO) model, SIRQ utilizes a 
        <span class="highlight">Real-Time Auction Mechanism</span> to prioritize access.
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown("""
            **The Core Logic:**
            * **🚛 Heterogeneous Agents:** Not all trucks are equal. Some have critical deadlines (high urgency), others can wait (low urgency).
            * **💸 Dynamic Bidding:** Drivers bid for charging slots based on their "Willingness-to-Pay".
            * **⚡ Optimization:** The system reorders the queue instantly, ensuring high-value logistics are prioritized over standard traffic.
            """)

        st.info("💡 **Key Insight:** FIFO is 'Fair' in time, but 'Inefficient' in value. SIRQ maximizes economic utility and grid efficiency.")

    with col_img:
        # Check if image exists to prevent error
        if os.path.exists("station_diagram.png"):
            st.image("station_diagram.png", caption="Fig 1: Station Layout - Separating Waiting (Queue) & Charging Zones ", use_column_width=True)
        else:
            st.warning("⚠️ Image 'station_diagram.png' not found. Please add it to the project folder.")
            st.markdown("*(Diagram placeholder: Waiting Area vs Charging Area)*")

    # --- SECTION B: THE INTERACTIVE TWIN ---
    st.divider()
    st.subheader("🔴 Live Digital Twin")
    st.markdown("Observe the behavior of the **Waiting Stage** and **Charging Hub** in real-time.")

    # Configuration Row
    with st.expander("⚙️ Simulation Settings & Legend", expanded=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("**Agent Legend:**")
            st.markdown("🟥 **Critical (VIP):** High Bid ($$$), Cannot Wait.")
            st.markdown("🟦 **Standard:** Normal Bid ($$), Normal Wait.")
            st.markdown("⬜ **Economy:** Low Bid ($), Patient.")
        with c2:
            st.markdown("**Control Panel:**")
            cc1, cc2, cc3 = st.columns(3)
            with cc1: load = st.select_slider("Traffic Density", ["Normal", "Heavy", "Extreme"], value="Heavy")
            with cc2: speed = st.select_slider("Sim Speed", ["Normal", "Fast"], value="Fast")
            with cc3: 
                st.write("")
                start_btn = st.button("▶️ Run Comparative Experiment", type="primary", use_container_width=True)

    # Simulation Execution
    if start_btn:
        st.write("---")
        load_map = {"Normal": 1.0, "Heavy": 1.2, "Extreme": 1.5}
        
        # Initialize Models
        cfg = {"traffic_multiplier": load_map[load]}
        fifo = ChargingStationModel(4, "FIFO", seed=42, user_config=cfg)
        sirq = ChargingStationModel(4, "SIRQ", seed=42, user_config=cfg)
        
        # Layout columns
        col_fifo, col_sirq = st.columns(2)
        
        with col_fifo: 
            st.subheader("🔵 Baseline (FIFO)")
            st.caption("Standard Queueing. Note how Red trucks get blocked.")
            ph_fifo = st.empty()
            metric_fifo = st.empty()
            
        with col_sirq: 
            st.subheader("🟢 SIRQ (Auction)")
            st.caption("Value-Based Priority. Note Red trucks jumping to front.")
            ph_sirq = st.empty()
            metric_sirq = st.empty()
            
        bar = st.progress(0)
        
        # Loop Settings
        skip = 5 if speed == "Normal" else 20
        sleep = 0.05 if speed == "Normal" else 0.001
        
        for i in range(1440):
            fifo.step()
            sirq.step()
            
            if i % skip == 0:
                bar.progress((i+1)/1440)
                
                # Visuals
                ph_fifo.markdown(render_station_visual(fifo), unsafe_allow_html=True)
                ph_sirq.markdown(render_station_visual(sirq), unsafe_allow_html=True)
                
                # Metrics
                metric_fifo.info(f"**Rev:** ${int(fifo.kpi_revenue)} | **Critical Failures:** {fifo.kpi_failed_critical}")
                metric_sirq.success(f"**Rev:** ${int(sirq.kpi_revenue)} | **Critical Failures:** {sirq.kpi_failed_critical}")
                
                time.sleep(sleep)
        st.success("Experiment Concluded.")


# =========================================================
# PAGE 2: SCIENTIFIC SIMULATION (Keep existing logic)
# =========================================================
elif page == "2. Scientific Simulation (Lab)":
    st.title("⚡ Scientific Validation (Monte Carlo)")
    st.markdown("Run **N** simulations to generate statistically significant data for analysis.")
    
    with st.form("mc_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_runs = st.number_input("Iterations (N)", 30, 200, 30)
            loads = st.multiselect("Traffic Scenarios", [0.8, 1.0, 1.2, 1.5, 2.0], default=[0.8, 1.0, 1.2, 1.5])
        with c2:
            st.markdown("Profile Mix:")
            pc = st.slider("Critical %", 0.0, 1.0, 0.2)
            ps = st.slider("Standard %", 0.0, 1.0, 0.6)
            pe = st.slider("Economy %", 0.0, 1.0, 0.2)
        
        run_btn = st.form_submit_button("🚀 Run Batch Experiment")
        
    if run_btn:
        results = []
        progress = st.progress(0)
        status = st.empty()
        total_steps = len(loads) * 2 * n_runs 
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
                    
                    log = pd.DataFrame(m.agent_log)
                    if not log.empty:
                        crit_w = log.query("Profile=='CRITICAL'")['Wait_Time'].mean()
                        eco_w = log.query("Profile=='ECONOMY'")['Wait_Time'].mean()
                    else: crit_w, eco_w = 0, 0
                        
                    results.append({
                        "Run_ID": i, "Traffic_Load": l, "Strategy": s,
                        "Revenue": m.kpi_revenue, "Critical_Failures": m.kpi_failed_critical,
                        "Avg_Wait_Critical": crit_w, "Avg_Wait_Economy": eco_w
                    })
                    curr += 1
                    if curr % 10 == 0:
                        progress.progress(curr/total_steps)
                        status.text(f"Processing... {curr}/{total_steps}")
                        
        st.session_state['monte_carlo_df'] = pd.DataFrame(results)
        st.success("Batch Complete. Go to 'Deep Dive Analytics'.")

# =========================================================
# PAGE 3: DEEP DIVE ANALYTICS
# =========================================================
elif page == "3. Deep Dive Analytics":
    st.title("📊 Scientific Deep Dive")
    
    df = st.session_state['monte_carlo_df']
    if df is None:
        st.warning("⚠️ No Data Found. Please run the simulation in Tab 2 or Import data in Tab 4.")
    else:
        plotter = ScientificPlotter(df)
        tab1, tab2, tab3 = st.tabs(["RQ1: Revenue Efficiency", "RQ2: Critical Reliability", "RQ3: Equity Cost"])
        
        with tab1:
            st.header("RQ1: Revenue Impact")
            st.markdown("Does the auction mechanism significantly increase daily turnover?")
            st.plotly_chart(plotter.rq1_revenue_ci(), use_container_width=True)
            with st.expander("Show Detailed Distributions"):
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plotter.rq1_revenue_dist(), use_container_width=True)
                with c2: 
                    d = plotter.rq1_revenue_delta()
                    if d: st.plotly_chart(d, use_container_width=True)

        with tab2:
            st.header("RQ2: Service Level Reliability")
            st.markdown("Are we successfully protecting the Critical Supply Chain?")
            st.plotly_chart(plotter.rq2_critical_wait_box(), use_container_width=True)
            with st.expander("Show Failure Rates & ECDF"):
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plotter.rq2_failure_rate(), use_container_width=True)
                with c2: st.plotly_chart(plotter.rq2_ecdf_wait(), use_container_width=True)

        with tab3:
            st.header("RQ3: Equity & Starvation")
            st.markdown("Quantifying the trade-off: How much do Economy drivers suffer?")
            st.plotly_chart(plotter.rq3_equity_gap(), use_container_width=True)
            with st.expander("Show Starvation Scatter"):
                st.plotly_chart(plotter.rq3_starvation_scatter(), use_container_width=True)

# =========================================================
# PAGE 4: DATA MANAGER
# =========================================================
elif page == "4. Data Manager":
    st.title("💾 Data Manager")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Export Data")
        if st.session_state['monte_carlo_df'] is not None:
            csv = st.session_state['monte_carlo_df'].to_csv(index=False).encode('utf-8')
            st.download_button("Download .csv", csv, "sirq_results.csv", "text/csv")
    with c2:
        st.subheader("Import Data")
        f = st.file_uploader("Upload CSV", type="csv")
        if f:
            st.session_state['monte_carlo_df'] = pd.read_csv(f)
            st.success("Loaded Successfully!")