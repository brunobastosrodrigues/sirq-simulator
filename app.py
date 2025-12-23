import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import io
import zipfile
from src.model import ChargingStationModel
from src.vis_utils import render_station_visual
from src.analytics import ScientificPlotter
from src.config import TRUCK_PROFILES

st.set_page_config(layout="wide", page_title="SIRQ Research Platform", page_icon="⚡")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Global Font Improvements */
    .big-font { font-size: 18px !important; color: #444; line-height: 1.6; }
    .highlight { color: #2e86c1; font-weight: 600; background-color: #e8f4f8; padding: 2px 6px; border-radius: 4px; }
    
    /* Modern Concept Box */
    .concept-box { 
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 25px; 
        border-radius: 12px; 
        border-left: 6px solid #2e86c1; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 25px; 
    }
    
    /* Clean Sidebar */
    .css-1d391kg { padding-top: 1rem; } /* Adjust sidebar padding */
    div[data-testid="stSidebarNav"] { display: none; } /* Hide default nav if any */
</style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if 'monte_carlo_df' not in st.session_state: st.session_state['monte_carlo_df'] = None
if 'agent_level_df' not in st.session_state: st.session_state['agent_level_df'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = "Concept & Demo"

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.header("SIRQ Platform")
    st.markdown("---")
    
    # Navigation using radio buttons
    page = st.radio(
        "Navigation",
        [
            "Concept & Demo", 
            "Scientific Simulation (Lab)", 
            "Deep Dive Analytics", 
            "Data Manager",
            "Discussion & Feasibility"
        ]
    )
    
    st.markdown("---")
    st.markdown("**Status:** Ready")
    st.caption("v2.1.0-ScienceBuild")

# =========================================================
# PAGE 1: CONCEPT & DEMO
# =========================================================
if page == "Concept & Demo":
    st.title("SIRQ: System for Interactive Reservation and Queueing")
    st.subheader("Redefining Logistics Infrastructure through Market Mechanics")
    
    st.divider()

    col_text, col_img = st.columns([1.2, 1])
    
    with col_text:
        st.markdown("""
        <div class="concept-box">
            <div class="big-font">
            <b>The Challenge:</b> 
            Modern logistics is heterogeneous. A truck carrying <i>perishable vaccines</i> ($150/hr loss) currently waits in the same line as a truck carrying <i>gravel</i> ($20/hr loss). This "First-Come-First-Served" (FIFO) inefficiency costs supply chains billions.
            <br><br>
            <b>The SIRQ Proposal:</b> 
            We replace the physical queue with a <span class="highlight">Virtual Auction</span>. 
            <br>
            Incoming vehicles bid for charging slots based on their real-time <b>Value of Time (VOT)</b>.
            <ul>
                <li>High-priority cargo (Medical/Cold Chain) can pay a premium to jump the queue.</li>
                <li>Flexible cargo (Economy) waits or charges during off-peak hours for a discount.</li>
                <li>Surplus revenue is redistributed to subsidize infrastructure or economy drivers.</li>
            </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_img:
        # Placeholder for the visual diagram
        # [cite_start] [cite: 1]
        if os.path.exists("station_diagram.png"):
            st.image("station_diagram.png", caption="Fig 1: SIRQ Auction Logic vs FIFO", use_column_width=True)
        else:
             st.info("Visual Diagram Placeholder (station_diagram.png not found)")

    # Interactive Demo
    st.divider()
    st.subheader("Interactive Digital Twin")
    st.markdown("Run a live comparison below. Watch how **Critical Agents (Red)** get stuck in FIFO but bypass queues in SIRQ.")
    
    with st.expander("⚙️ Configure Simulation Parameters", expanded=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("**Agent Types:**")
            st.markdown("- <span style='color:red'><b>Critical</b></span>: High Value. Bids aggressively.", unsafe_allow_html=True)
            st.markdown("- <span style='color:blue'><b>Standard</b></span>: Medium Value.", unsafe_allow_html=True)
            st.markdown("- <span style='color:grey'><b>Economy</b></span>: Low Value. Price sensitive.", unsafe_allow_html=True)
        with c2:
            cc1, cc2, cc3 = st.columns(3)
            with cc1: load = st.select_slider("Traffic Density", ["Normal", "Heavy", "Extreme"], value="Heavy")
            with cc2: speed = st.select_slider("Animation Speed", ["Normal", "Fast"], value="Fast")
            with cc3: 
                st.write("")
                start_btn = st.button("▶️ Start Simulation", type="primary", use_container_width=True)

    if start_btn:
        st.write("---")
        load_map = {"Normal": 1.0, "Heavy": 1.2, "Extreme": 1.5}
        cfg = {"traffic_multiplier": load_map[load]}
        
        # Initialize Twin Models
        fifo = ChargingStationModel(4, "FIFO", seed=42, user_config=cfg)
        sirq = ChargingStationModel(4, "SIRQ", seed=42, user_config=cfg)
        
        c1, c2 = st.columns(2)
        with c1: st.subheader("Baseline (FIFO)"); ph1=st.empty(); m1=st.empty()
        with c2: st.subheader("SIRQ (Auction)"); ph2=st.empty(); m2=st.empty()
        
        bar = st.progress(0)
        skip = 5 if speed == "Normal" else 20
        sleep_time = 0.05 if speed == "Normal" else 0.001
        
        for i in range(1440):
            fifo.step(); sirq.step()
            if i % skip == 0:
                bar.progress((i+1)/1440)
                # Visual Rendering
                ph1.markdown(render_station_visual(fifo), unsafe_allow_html=True)
                ph2.markdown(render_station_visual(sirq), unsafe_allow_html=True)
                
                # Live Metrics
                m1.info(f"**Rev:** ${int(fifo.kpi_revenue)} | **Failures:** {fifo.kpi_failed_critical}\n\n**Price:** ${fifo.current_price:.2f}/kWh | **Lost:** {fifo.kpi_balked_agents}")
                m2.success(f"**Rev:** ${int(sirq.kpi_revenue)} | **Failures:** {sirq.kpi_failed_critical}\n\n**Price:** ${sirq.current_price:.2f}/kWh | **Lost:** {sirq.kpi_balked_agents}")
                time.sleep(sleep_time)

# =========================================================
# PAGE 2: SCIENTIFIC SIMULATION
# =========================================================
elif page == "Full Simulation":
    st.title("Monte Carlo Simulation")
    st.markdown("Run thousands of iterations across varying traffic loads.")
    
    with st.expander("View Economic Parameters", expanded=False):
        st.dataframe(pd.DataFrame(TRUCK_PROFILES).T[["vot_range", "patience", "max_price_tolerance"]], use_container_width=True)
    
    with st.form("mc_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_runs = st.number_input("Iterations per Scenario (N)", 30, 200, 30)
            loads = st.multiselect("Traffic Scenarios (Multiplier)", [0.8, 1.0, 1.2, 1.5, 2.0], default=[0.8, 1.0, 1.2, 1.5])
        with c2:
            st.markdown("Traffic Composition:")
            pc = st.slider("Critical %", 0.0, 1.0, 0.2); ps = st.slider("Standard %", 0.0, 1.0, 0.6); pe = st.slider("Economy %", 0.0, 1.0, 0.2)
        run_btn = st.form_submit_button("🚀 Run Batch Experiment")
        
    if run_btn:
        results, micro_dump = [], []
        prog = st.progress(0); stat = st.empty()
        total = len(loads) * 2 * n_runs; curr = 0
        base = {"prob_critical": pc, "prob_standard": ps, "prob_economy": pe}
        
        for l in loads:
            for s in ["FIFO", "SIRQ"]:
                for i in range(n_runs):
                    seed = np.random.randint(100000, 999999)
                    cfg = base.copy(); cfg["traffic_multiplier"] = l
                    m = ChargingStationModel(4, s, seed=seed, user_config=cfg)
                    for _ in range(1440): m.step()
                    
                    # Data Logging
                    log = pd.DataFrame(m.agent_log)
                    sys_log = pd.DataFrame(m.system_log)
                    
                    cw = log.query("Profile=='CRITICAL'")['Wait_Time'].mean() if not log.empty else 0
                    ew = log.query("Profile=='ECONOMY'")['Wait_Time'].mean() if not log.empty else 0
                    avg_sys_price = sys_log["Current_Price"].mean() if not sys_log.empty else 0.50
                    
                    results.append({
                        "Run_ID": i, "Traffic_Load": l, "Strategy": s, 
                        "Revenue": m.kpi_revenue, 
                        "Critical_Failures": m.kpi_failed_critical, 
                        "Avg_Wait_Critical": cw, "Avg_Wait_Economy": ew, 
                        "Balked_Agents": m.kpi_balked_agents, 
                        "Preemptions": m.kpi_preemptions,
                        "Avg_System_Price": avg_sys_price
                    })
                    
                    # Micro-log capture (First run only to save memory)
                    if i == 0:
                        log["Run_ID"] = i; log["Traffic_Load"] = l
                        micro_dump.append(log)
                    
                    curr += 1
                    if curr % 5 == 0: prog.progress(curr/total); stat.text(f"Simulating {curr}/{total}")
        
        st.session_state['monte_carlo_df'] = pd.DataFrame(results)
        st.session_state['agent_level_df'] = pd.concat(micro_dump) if micro_dump else None
        st.success("Experiment Complete. Navigate to 'Deep Dive Analytics' to view results.")

# =========================================================
# PAGE 3: DEEP DIVE ANALYTICS
# =========================================================
elif page == "Deep Dive Analytics":
    st.title("Analytics Suite")
    
    df = st.session_state['monte_carlo_df']
    df_micro = st.session_state['agent_level_df']
    
    if df is None:
        st.warning("⚠️ No Data. Please run a simulation in the 'Scientific Simulation' tab or Import data.")
    else:
        plotter = ScientificPlotter(df, df_micro)
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Efficiency", "Reliability", "Rationality", "Equity", "🔥 Advanced Heatmaps"])
        
        with tab1:
            st.header("RQ1: Economic Efficiency")
            st.plotly_chart(plotter.rq1_revenue_ci(), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(plotter.rq1_revenue_dist(), use_container_width=True)
            with c2: st.plotly_chart(plotter.rq1_revenue_delta(), use_container_width=True)
            
            c3, c4 = st.columns(2)
            with c3: st.plotly_chart(plotter.rq1_utilization_proxy(), use_container_width=True)
            with c4: st.plotly_chart(plotter.rq1_revenue_stability(), use_container_width=True)

        with tab2:
            st.header("RQ2: Service Reliability")
            st.plotly_chart(plotter.rq2_critical_wait_box(), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(plotter.rq2_failure_rate(), use_container_width=True)
            with c2: st.plotly_chart(plotter.rq2_ecdf_wait(), use_container_width=True)
            
            c3, c4 = st.columns(2)
            with c3: 
                f = plotter.rq2_max_wait_analysis()
                if f: st.plotly_chart(f, use_container_width=True)
            with c4: 
                f = plotter.rq2_on_time_performance()
                if f: st.plotly_chart(f, use_container_width=True)

        with tab3:
            st.header("RQ3: Pricing Dynamics")
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(plotter.rq3_price_trend(), use_container_width=True)
            with c2: st.plotly_chart(plotter.rq3_demand_loss(), use_container_width=True)
            
            st.divider()
            st.subheader("Agent Behavior")
            if df_micro is not None:
                c3, c4 = st.columns(2)
                with c3: st.plotly_chart(plotter.rq3_bidding_rationality(), use_container_width=True)
                with c4: st.plotly_chart(plotter.rq3_winning_bid_trend(), use_container_width=True)
            else:
                st.warning("Micro-data missing.")
            st.plotly_chart(plotter.rq3_welfare_loss(), use_container_width=True)

        with tab4:
            st.header("RQ4: Social Equity")
            if df_micro is not None:
                st.plotly_chart(plotter.rq4_price_paid_by_profile(), use_container_width=True)
            
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(plotter.rq4_equity_gap(), use_container_width=True)
            with c2: st.plotly_chart(plotter.rq4_starvation_scatter(), use_container_width=True)
            
            st.divider()
            st.subheader("Policy Solution: Redistribution")
            st.plotly_chart(plotter.rq4_subsidy_potential(), use_container_width=True)

        with tab5:
            st.header("Sensitivity & Multi-Variable Analysis")
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(plotter.plot_sensitivity_heatmap(metric="Revenue"), use_container_width=True)
            with col2:
                st.plotly_chart(plotter.plot_sensitivity_heatmap(metric="Avg_Wait_Critical"), use_container_width=True)
        
            st.divider()
            
            col3, col4 = st.columns(2)
            with col3:
                st.plotly_chart(plotter.plot_correlation_matrix(), use_container_width=True)
            with col4:
                st.plotly_chart(plotter.plot_balking_heatmap(), use_container_width=True)
                
            st.divider()
            st.subheader("3D Frontier Analysis")
            st.plotly_chart(plotter.plot_3d_efficiency_surface(), use_container_width=True)

# =========================================================
# PAGE 4: DATA MANAGER
# =========================================================
elif page == "Data Manager":
    st.title("Data Manager")
    st.markdown("Export or Import experiment data (ZIP format) to save your work or share with peers.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Export")
        if st.session_state['monte_carlo_df'] is not None:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("summary.csv", st.session_state['monte_carlo_df'].to_csv(index=False))
                if st.session_state['agent_level_df'] is not None:
                    zf.writestr("micro.csv", st.session_state['agent_level_df'].to_csv(index=False))
            st.download_button("Download Data (.zip)", buf.getvalue(), "sirq_experiment.zip", "application/zip")
        else:
            st.info("No data available to export.")
            
    with c2:
        st.subheader("Import")
        f = st.file_uploader("Upload .zip file", type="zip")
        if f:
            try:
                with zipfile.ZipFile(f, "r") as zf:
                    st.session_state['monte_carlo_df'] = pd.read_csv(io.BytesIO(zf.read("summary.csv")))
                    if "micro.csv" in zf.namelist():
                        st.session_state['agent_level_df'] = pd.read_csv(io.BytesIO(zf.read("micro.csv")))
                st.success("Data successfully loaded!")
            except Exception as e:
                st.error(f"Import failed: {e}")

# =========================================================
# PAGE 5: DISCUSSION
# =========================================================
elif page == "Discussion & Feasibility":
    st.title("Discussion: From Theory to Practice")
    
    st.header("Technical Feasibility")
    st.markdown("""
    Implementing SIRQ in the real world requires specific infrastructure updates:
    * **OCPP 2.0.1+:** Chargers must support the *Open Charge Point Protocol* (OCPP) for remote command overrides and dynamic tariffs.
    * **Edge Computing:** An auction engine needs < 500ms latency; a local edge controller is recommended over pure cloud solutions.
    * **Plug & Charge (ISO 15118):** Automated identification is crucial. Drivers cannot manually bid via app while driving; the truck's computer must auto-negotiate based on pre-set preferences.
    """)
    
    st.divider()
    
    st.header("Social Implications")
    st.markdown("""
    **The Risk: Energy Gentrification**
    Without regulation, auctions may exclude small operators (Economy) from charging during prime hours entirely.
    
    **The Solution: The 'Robin Hood' Protocol**
    Our analytics (RQ4) show SIRQ generates surplus revenue. We propose a policy where:
    1. **50% of Surplus** is retained by the Operator (Profit Incentive).
    2. **50% of Surplus** is redistributed as *Discount Tokens* to drivers who waited > 30 minutes.
    
    This ensures that while wealthy agents buy *Time*, economy agents gain *Purchasing Power*.
    """)