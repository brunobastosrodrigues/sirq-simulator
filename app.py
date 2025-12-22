import streamlit as st
import pandas as pd
import numpy as np
import time
import os
from src.model import ChargingStationModel
from src.vis_utils import render_station_visual
from src.analytics import ScientificPlotter
from src.config import TRUCK_PROFILES  # Import profiles for display

st.set_page_config(layout="wide", page_title="SIRQ Simulator", page_icon="⚡")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .big-font { font-size: 20px !important; color: #555; }
    .highlight { color: #2e86c1; font-weight: bold; }
    .stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

if 'monte_carlo_df' not in st.session_state: st.session_state['monte_carlo_df'] = None
if 'agent_level_df' not in st.session_state: st.session_state['agent_level_df'] = None # New state for micro-data

st.sidebar.header("⚡ SIRQ Platform")
page = st.sidebar.radio("Navigate", [
    "1. Concept & Demo", 
    "2. Scientific Simulation (Lab)", 
    "3. Deep Dive Analytics", 
    "4. Data Manager"
])

# =========================================================
# PAGE 1: CONCEPT & DEMO 
# =========================================================
if page == "1. Concept & Demo":
    st.title("SIRQ: System for Interactive Reservation and Queueing")
    st.markdown("##### *A Market-Based Approach to Electric Truck Charging*")
    st.divider()
    col_text, col_img = st.columns([1.2, 1])
    with col_text:
        st.markdown("""
        <div class="big-font">
        <b>SIRQ</b> utilizes a <span class="highlight">Real-Time Auction Mechanism</span> to prioritize access based on Value of Time.
        </div>
        """, unsafe_allow_html=True)
        st.info("💡 **Key Insight:** FIFO is 'Fair' in time, but 'Inefficient' in value.")
    with col_img:
        if os.path.exists("station_diagram.png"):
            st.image("station_diagram.png", caption="Fig 1: Station Layout", use_column_width=True)

    st.divider()
    st.subheader("🔴 Live Digital Twin")
    with st.expander("⚙️ Simulation Settings", expanded=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.caption("Agent Legend")
            st.markdown("🟥 **Critical (VIP):** High VOT ($150+/hr)")
            st.markdown("🟦 **Standard:** Medium VOT ($65/hr)")
            st.markdown("⬜ **Economy:** Low VOT ($20/hr)")
        with c2:
            cc1, cc2, cc3 = st.columns(3)
            with cc1: load = st.select_slider("Traffic", ["Normal", "Heavy", "Extreme"], value="Heavy")
            with cc2: speed = st.select_slider("Speed", ["Normal", "Fast"], value="Fast")
            with cc3: 
                st.write(""); start_btn = st.button("▶️ Run Demo", type="primary", use_container_width=True)

    if start_btn:
        st.write("---")
        load_map = {"Normal": 1.0, "Heavy": 1.2, "Extreme": 1.5}
        cfg = {"traffic_multiplier": load_map[load]}
        fifo = ChargingStationModel(4, "FIFO", seed=42, user_config=cfg)
        sirq = ChargingStationModel(4, "SIRQ", seed=42, user_config=cfg)
        col_fifo, col_sirq = st.columns(2)
        with col_fifo: st.subheader("🔵 FIFO"); ph_fifo = st.empty(); m_fifo = st.empty()
        with col_sirq: st.subheader("🟢 SIRQ"); ph_sirq = st.empty(); m_sirq = st.empty()
        bar = st.progress(0)
        skip = 5 if speed == "Normal" else 20
        sleep = 0.05 if speed == "Normal" else 0.001
        
        for i in range(1440):
            fifo.step(); sirq.step()
            if i % skip == 0:
                bar.progress((i+1)/1440)
                ph_fifo.markdown(render_station_visual(fifo), unsafe_allow_html=True)
                ph_sirq.markdown(render_station_visual(sirq), unsafe_allow_html=True)
                m_fifo.info(f"Rev: ${int(fifo.kpi_revenue)} | Fail: {fifo.kpi_failed_critical}")
                m_sirq.success(f"Rev: ${int(sirq.kpi_revenue)} | Fail: {sirq.kpi_failed_critical}")
                time.sleep(sleep)
        st.success("Demo Complete.")

# =========================================================
# PAGE 2: SCIENTIFIC SIMULATION (With Profile Inspector)
# =========================================================
elif page == "2. Scientific Simulation (Lab)":
    st.title("⚡ Scientific Validation")
    st.markdown("Run batch simulations to generate statistical evidence.")
    
    # --- NEW: PROFILE INSPECTOR ---
    with st.expander("ℹ️ Inspect Economic Agent Profiles (Micro-Foundations)", expanded=False):
        st.markdown("""
        These profiles define the **Economic Rationality** of the agents. 
        * **VOT (Value of Time):** The monetary cost of waiting 1 hour.
        * **Patience:** How long they wait before abandoning the queue.
        """)
        # Convert dictionary to DataFrame for nice display
        df_profiles = pd.DataFrame(TRUCK_PROFILES).T
        df_profiles = df_profiles[["vot_range", "patience", "urgency_range"]]
        st.dataframe(df_profiles, use_container_width=True)
    
    with st.form("mc_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_runs = st.number_input("Iterations (N)", 30, 200, 30)
            loads = st.multiselect("Traffic Scenarios", [0.8, 1.0, 1.2, 1.5, 2.0], default=[0.8, 1.0, 1.2, 1.5])
        with c2:
            st.markdown("**Traffic Mix:**")
            pc = st.slider("Critical %", 0.0, 1.0, 0.2)
            ps = st.slider("Standard %", 0.0, 1.0, 0.6)
            pe = st.slider("Economy %", 0.0, 1.0, 0.2)
        
        run_btn = st.form_submit_button("🚀 Run Batch Experiment")
        
    if run_btn:
        results = []
        agent_data_dump = [] # To store micro-data for scatter plots
        progress = st.progress(0)
        status = st.empty()
        total_steps = len(loads) * 2 * n_runs 
        curr = 0
        base_cfg = {"prob_critical": pc, "prob_standard": ps, "prob_economy": pe}
        
        for l in loads:
            for s in ["FIFO", "SIRQ"]:
                for i in range(n_runs):
                    seed = np.random.randint(100000, 999999)
                    cfg = base_cfg.copy(); cfg["traffic_multiplier"] = l
                    m = ChargingStationModel(4, s, seed=seed, user_config=cfg)
                    for _ in range(1440): m.step()
                    
                    log = pd.DataFrame(m.agent_log)
                    if not log.empty:
                        crit_w = log.query("Profile=='CRITICAL'")['Wait_Time'].mean()
                        eco_w = log.query("Profile=='ECONOMY'")['Wait_Time'].mean()
                        
                        # Store a sample of agent data for Micro-Analysis (only for last run to save memory)
                        if i == 0: 
                            log["Run_ID"] = i; log["Traffic_Load"] = l
                            agent_data_dump.append(log)
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
        if agent_data_dump:
            st.session_state['agent_level_df'] = pd.concat(agent_data_dump)
        st.success("Batch Complete. Go to 'Deep Dive Analytics'.")

# =========================================================
# PAGE 3: DEEP DIVE ANALYTICS
# =========================================================
elif page == "3. Deep Dive Analytics":
    st.title("📊 Scientific Deep Dive")
    
    df = st.session_state['monte_carlo_df']
    df_micro = st.session_state['agent_level_df']
    
    if df is None:
        st.warning("⚠️ No Data. Run Simulation in Tab 2.")
    else:
        plotter = ScientificPlotter(df)
        
        # We need a separate plotter instance or method for micro data
        # We'll just pass the micro df to new methods if needed, or handle plotting here using plotly
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "RQ1: Macro-Economics", 
            "RQ2: Service Reliability", 
            "RQ3: Micro-Decisions", 
            "RQ4: Societal Impact"
        ])
        
        with tab1:
            st.header("RQ1: Revenue & Efficiency")
            st.plotly_chart(plotter.rq1_revenue_ci(), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(plotter.rq1_revenue_dist(), use_container_width=True)
            with c2: 
                d = plotter.rq1_revenue_delta()
                if d: st.plotly_chart(d, use_container_width=True)

        with tab2:
            st.header("RQ2: Critical Supply Chain Protection")
            st.plotly_chart(plotter.rq2_critical_wait_box(), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(plotter.rq2_failure_rate(), use_container_width=True)
            with c2: st.plotly_chart(plotter.rq2_ecdf_wait(), use_container_width=True)

        with tab3:
            st.header("RQ3: Micro-Economic Behavior")
            st.markdown("*Are agents bidding rationally based on their Value of Time?*")
            
            if df_micro is not None:
                plotter_micro = ScientificPlotter(df_micro) # Reuse class for styling
                st.plotly_chart(plotter_micro.rq3_bidding_rationality(), use_container_width=True)
            else:
                st.info("Micro-data not available. Re-run simulation to capture agent-level decisions.")
            
            st.markdown("### Welfare Analysis")
            st.markdown("Comparing the 'Economic Pain' (Wait Time × Value of Time).")
            st.plotly_chart(plotter.rq3_welfare_loss(), use_container_width=True)

        with tab4:
            st.header("RQ4: Societal Impact & Equity")
            st.markdown("""
            **The Challenge:** SIRQ increases efficiency but may increase wait times for Economy drivers.
            **The Solution:** Use the 'Extra Revenue' generated to subsidize charging costs for those who wait.
            """)
            
            st.plotly_chart(plotter.rq4_equity_gap(), use_container_width=True)
            
            st.divider()
            st.subheader("💰 Redistribution Potential")
            st.markdown("This chart shows the **Surplus Revenue** available. If distributed as a rebate to Economy drivers, we can achieve **Pareto Improvement** (Winners gain, Losers don't lose).")
            d = plotter.rq4_subsidy_potential()
            if d: st.plotly_chart(d, use_container_width=True)
            else: st.warning("Need both SIRQ and FIFO data to calculate subsidy pool.")

#