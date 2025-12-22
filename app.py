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
    .big-font { font-size: 20px !important; color: #555; line-height: 1.5; }
    .highlight { color: #2e86c1; font-weight: bold; }
    .concept-box { background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #2e86c1; margin-bottom: 20px; }
    .stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if 'monte_carlo_df' not in st.session_state: st.session_state['monte_carlo_df'] = None
if 'agent_level_df' not in st.session_state: st.session_state['agent_level_df'] = None

st.sidebar.header("⚡ SIRQ Research")
page = st.sidebar.radio("Navigate", [
    "1. Concept & Demo", 
    "2. Scientific Simulation (Lab)", 
    "3. Deep Dive Analytics", 
    "4. Data Manager",
    "5. Discussion & Feasibility"
])

# =========================================================
# PAGE 1: CONCEPT & DEMO
# =========================================================
if page == "1. Concept & Demo":
    st.title("SIRQ: System for Interactive Reservation and Queueing")
    st.markdown("#### *A Market-Based Mechanism for Electric Logistics Infrastructure*")
    
    st.divider()

    col_text, col_img = st.columns([1.3, 1])
    
    with col_text:
        st.markdown("""
        <div class="concept-box">
        <div class="big-font">
        <b>The Problem:</b> Traditional "First-Come-First-Served" (FIFO) queues are inefficient for heterogeneous logistics. 
        A truck carrying perishable medicine often waits behind a truck carrying gravel, simply because it arrived 5 minutes later.
        <br><br>
        <b>The Solution:</b> SIRQ implements a <span class="highlight">Real-Time Vickrey-Clarke-Groves (VCG) Inspired Auction</span>. 
        Agents bid for slots based on their Value of Time (VOT). The system dynamically reorders the queue to minimize aggregate economic loss.
        </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        **Core Mechanisms:**
        * **Dynamic Prioritization:** The queue is sorted by Bid Price, not Arrival Time.
        * **Preemption:** High-value agents can "bump" low-value agents (with a price premium).
        * **Smart Pricing (New):** Prices now surge dynamically with congestion, causing price-sensitive agents to balk.
        * **Economic Agents:** Simulation agents act rationally based on their specific *Value of Time* profiles.
        """)

    with col_img:
        if os.path.exists("station_diagram.png"):
            st.image("station_diagram.png", caption="Fig 1: SIRQ Station Topology", use_column_width=True)
        else:
            st.warning("Diagram not found. Please upload 'station_diagram.png'.")

    # Interactive Demo
    st.divider()
    st.subheader("🔴 Live Digital Twin")
    
    with st.expander("⚙️ Simulation Settings & Legend", expanded=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("**Agent Legend:**")
            st.markdown("🟥 **Critical (VIP):** High VOT ($150+/hr). Bids aggressively.")
            st.markdown("🟦 **Standard:** Medium VOT ($65/hr).")
            st.markdown("⬜ **Economy:** Low VOT ($20/hr). Elastic demand.")
        with c2:
            st.markdown("**Control Panel:**")
            cc1, cc2, cc3 = st.columns(3)
            with cc1: load = st.select_slider("Traffic Density", ["Normal", "Heavy", "Extreme"], value="Heavy")
            with cc2: speed = st.select_slider("Sim Speed", ["Normal", "Fast"], value="Fast")
            with cc3: 
                st.write("")
                start_btn = st.button("▶️ Run Comparative Demo", type="primary", use_container_width=True)

    if start_btn:
        st.write("---")
        load_map = {"Normal": 1.0, "Heavy": 1.2, "Extreme": 1.5}
        cfg = {"traffic_multiplier": load_map[load]}
        fifo = ChargingStationModel(4, "FIFO", seed=42, user_config=cfg)
        sirq = ChargingStationModel(4, "SIRQ", seed=42, user_config=cfg)
        
        c1, c2 = st.columns(2)
        with c1: st.subheader("🔵 FIFO (Baseline)"); ph1=st.empty(); m1=st.empty()
        with c2: st.subheader("🟢 SIRQ (Proposed)"); ph2=st.empty(); m2=st.empty()
        
        bar = st.progress(0)
        skip = 5 if speed == "Normal" else 20
        sleep = 0.05 if speed == "Normal" else 0.001
        
        for i in range(1440):
            fifo.step(); sirq.step()
            if i % skip == 0:
                bar.progress((i+1)/1440)
                ph1.markdown(render_station_visual(fifo), unsafe_allow_html=True)
                ph2.markdown(render_station_visual(sirq), unsafe_allow_html=True)
                m1.info(f"Rev: ${int(fifo.kpi_revenue)} | Failures: {fifo.kpi_failed_critical}")
                m2.success(f"Rev: ${int(sirq.kpi_revenue)} | Failures: {sirq.kpi_failed_critical}")
                time.sleep(sleep)

# =========================================================
# PAGE 2: SCIENTIFIC SIMULATION
# =========================================================
elif page == "2. Scientific Simulation (Lab)":
    st.title("⚡ Scientific Validation (Monte Carlo)")
    st.markdown("Generate statistical evidence by running **N** simulations per scenario.")
    
    with st.expander("ℹ️ Inspect Economic Agent Profiles", expanded=False):
        st.dataframe(pd.DataFrame(TRUCK_PROFILES).T[["vot_range", "patience", "urgency_range", "max_price_tolerance"]], use_container_width=True)
    
    with st.form("mc_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_runs = st.number_input("Iterations (N)", 30, 200, 30)
            loads = st.multiselect("Traffic Scenarios", [0.8, 1.0, 1.2, 1.5, 2.0], default=[0.8, 1.0, 1.2, 1.5])
        with c2:
            st.markdown("Traffic Mix:")
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
                    
                    # Log Summary
                    log = pd.DataFrame(m.agent_log)
                    cw = log.query("Profile=='CRITICAL'")['Wait_Time'].mean() if not log.empty else 0
                    ew = log.query("Profile=='ECONOMY'")['Wait_Time'].mean() if not log.empty else 0
                    results.append({"Run_ID": i, "Traffic_Load": l, "Strategy": s, "Revenue": m.kpi_revenue, "Critical_Failures": m.kpi_failed_critical, "Avg_Wait_Critical": cw, "Avg_Wait_Economy": ew, "Balked_Agents": m.kpi_balked_agents, "Preemptions": m.kpi_preemptions})
                    
                    # Log Micro (Only 1 run per config to save RAM)
                    if i == 0:
                        log["Run_ID"] = i; log["Traffic_Load"] = l
                        micro_dump.append(log)
                    
                    curr += 1; 
                    if curr % 5 == 0: prog.progress(curr/total); stat.text(f"Simulating {curr}/{total}")
        
        st.session_state['monte_carlo_df'] = pd.DataFrame(results)
        st.session_state['agent_level_df'] = pd.concat(micro_dump) if micro_dump else None
        st.success("Batch Complete. Go to 'Deep Dive Analytics'.")

# =========================================================
# PAGE 3: DEEP DIVE ANALYTICS
# =========================================================
elif page == "3. Deep Dive Analytics":
    st.title("📊 Scientific Analytics Suite")
    
    df = st.session_state['monte_carlo_df']
    df_micro = st.session_state['agent_level_df']
    
    if df is None:
        st.warning("⚠️ No Data Found. Please run the simulation in Tab 2 or Import data in Tab 4.")
    else:
        plotter = ScientificPlotter(df, df_micro)
        
        tab1, tab2, tab3, tab4 = st.tabs(["RQ1: Efficiency", "RQ2: Reliability", "RQ3: Micro-Econ", "RQ4: Equity"])
        
        with tab1:
            st.header("RQ1: Economic Efficiency & Utilization")
            st.plotly_chart(plotter.rq1_revenue_ci(), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(plotter.rq1_revenue_dist(), use_container_width=True)
            with c2: st.plotly_chart(plotter.rq1_revenue_delta(), use_container_width=True)
            c3, c4 = st.columns(2)
            with c3: st.plotly_chart(plotter.rq1_utilization_proxy(), use_container_width=True)
            with c4: st.plotly_chart(plotter.rq1_opportunity_cost(), use_container_width=True)
            st.plotly_chart(plotter.rq1_revenue_stability(), use_container_width=True)
            st.markdown("### 🏷️ Smart Pricing Dynamics")
            st.plotly_chart(plotter.rq1_pricing_dynamics(), use_container_width=True)

        with tab2:
            st.header("RQ2: Service Reliability (Critical Chains)")
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
            f = plotter.rq2_preemption_turbulence()
            if f: st.plotly_chart(f, use_container_width=True)

        with tab3:
            st.header("RQ3: Micro-Economic Rationality")
            if df_micro is not None:
                st.plotly_chart(plotter.rq3_bidding_rationality(), use_container_width=True)
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plotter.rq3_bid_landscape(), use_container_width=True)
                with c2: st.plotly_chart(plotter.rq3_winning_bid_trend(), use_container_width=True)
                st.plotly_chart(plotter.rq3_profile_win_rate(), use_container_width=True)
            else:
                st.warning("Micro-data missing. Re-run simulation.")
            st.plotly_chart(plotter.rq3_welfare_loss(), use_container_width=True)

        with tab4:
            st.header("RQ4: Social Equity & Redistribution")
            st.plotly_chart(plotter.rq4_equity_gap(), use_container_width=True)
            st.plotly_chart(plotter.rq4_starvation_scatter(), use_container_width=True) # RESTORED
            c1, c2 = st.columns(2)
            with c1: 
                f = plotter.rq4_gini_coefficient()
                if f: st.plotly_chart(f, use_container_width=True)
            with c2: 
                f = plotter.rq4_starvation_depth()
                if f: st.plotly_chart(f, use_container_width=True)
            
            st.divider()
            st.subheader("💰 Policy Solution: Redistribution")
            st.plotly_chart(plotter.rq4_subsidy_potential(), use_container_width=True)
            st.plotly_chart(plotter.rq4_access_rate(), use_container_width=True)

# =========================================================
# PAGE 4: DATA MANAGER (FIXED ZIP SUPPORT)
# =========================================================
elif page == "4. Data Manager":
    st.title("💾 Data Manager (ZIP Support)")
    st.markdown("Export/Import full experiment data (Summary + Micro-logs) for reproducibility.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📤 Export Experiment")
        if st.session_state['monte_carlo_df'] is not None:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("summary.csv", st.session_state['monte_carlo_df'].to_csv(index=False))
                if st.session_state['agent_level_df'] is not None:
                    zf.writestr("micro.csv", st.session_state['agent_level_df'].to_csv(index=False))
            st.download_button("Download Experiment.zip", buf.getvalue(), "sirq_experiment.zip", "application/zip")
        else:
            st.info("No data to export.")
            
    with c2:
        st.subheader("📥 Import Experiment")
        f = st.file_uploader("Upload .zip", type="zip")
        if f:
            try:
                with zipfile.ZipFile(f, "r") as zf:
                    st.session_state['monte_carlo_df'] = pd.read_csv(io.BytesIO(zf.read("summary.csv")))
                    if "micro.csv" in zf.namelist():
                        st.session_state['agent_level_df'] = pd.read_csv(io.BytesIO(zf.read("micro.csv")))
                st.success("Experiment Loaded! Go to Analytics.")
            except Exception as e:
                st.error(f"Error: {e}")

# =========================================================
# PAGE 5: DISCUSSION & FEASIBILITY (NEW)
# =========================================================
elif page == "5. Discussion & Feasibility":
    st.title("📝 Discussion: Moving from Theory to Practice")
    
    st.header("1. Technical Requirements")
    st.markdown("""
    To implement SIRQ in the real world, the following technical stack is required:
    * **OCPP 2.0.1+ Support:** The chargers must support the *Open Charge Point Protocol* (OCPP) to allow remote command overrides and dynamic tariff pushing.
    * **Low-Latency Edge Computing:** The Auction Engine cannot run solely on the cloud. A local edge controller is recommended to handle bidding resolution within < 500ms.
    * **Automated Identification (Plug & Charge / ISO 15118):** Trucks must be identified automatically to retrieve their Profile/Wallet. Manual app entry is too slow for high-throughput logistics.
    """)
    
    st.divider()
    
    st.header("2. Social Impact & Policy")
    st.markdown("""
    **The Risk:** Without regulation, auction systems can lead to "Energy Gentrification," where small operators (Economy) are permanently excluded from prime-time charging.
    
    **The Mitigation (The 'Robin Hood' Protocol):**
    As shown in the Analytics (RQ4), SIRQ generates significant *Surplus Revenue*. A policy enforcement layer can mandate that:
    1.  **50% of Surplus** is retained by the CPO (Incentive).
    2.  **50% of Surplus** is redistributed as a **Discount Token** to drivers who waited > 30 minutes.
    
    This ensures that while wealthy agents buy *Time*, economy agents gain *Purchasing Power*.
    """)
    
    st.divider()
    
    st.header("3. Limitations of Study")
    st.info("""
    * **Assumption of Rationality:** Real humans may bid irrationally (Winner's Curse) or out of panic.
    * **Single Station Model:** Does not account for network effects (drivers driving to a neighbor station).
    * **Perfect Information:** Agents in this sim know the exact queue length. In reality, estimates are noisy.
    """)