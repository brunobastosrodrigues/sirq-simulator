import streamlit as st
import pandas as pd
import numpy as np
import time
from src.model import ChargingStationModel
from src.vis_utils import render_station_visual
from src.analytics import ScientificPlotter

st.set_page_config(layout="wide", page_title="SIRQ Intelligent Charging")

# --- SIDEBAR & SETUP ---
if 'monte_carlo_df' not in st.session_state: st.session_state['monte_carlo_df'] = None

st.sidebar.title("⚡ SIRQ Platform")
page = st.sidebar.radio("Navigate", [
    "1. Business Value Demo", 
    "2. Scientific Simulation (Lab)", 
    "3. Deep Dive Analytics", 
    "4. Data Manager"
])

# =========================================================
# PAGE 1: BUSINESS VALUE DEMO (The "Pitch")
# =========================================================
if page == "1. SIRQ Concept":
    # --- HERO SECTION ---
    st.title("🚛 Stop Losing Revenue to Inefficient Queues")
    st.markdown("""
    **The Problem:** In traditional charging stations (FIFO), a high-value logistics truck willing to pay **$100** often gets stuck behind a casual driver paying **$20**, simply because the casual driver arrived 2 minutes earlier.
    
    **The Solution:** SIRQ (System for Interactive Reservation and Queueing) uses a real-time **Auction Mechanism**. 
    Drivers bid for priority. The station automatically reorders the queue to maximize revenue and ensure critical deliveries never wait.
    """)

    st.divider()

    # --- LEGEND & CONFIG ---
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Drivers on the Road")
        st.info("🔴 **VIP Logistics (Critical)**\n\n**Willing to Pay:** 5x Premium\n**Urgency:** High (Cannot Wait)")
        st.info("🔵 **Standard Fleet**\n\n**Willing to Pay:** Standard Rate\n**Urgency:** Normal")
        st.info("⚪ **Economy / Locals**\n\n**Willing to Pay:** Low (Price Sensitive)\n**Urgency:** Low (Will wait)")

    with c2:
        st.subheader("⚡ Live Operation Twin")
        st.write("Compare **Legacy Operations** vs. **SIRQ Smart Optimization** in real-time.")
        
        # Simple Controls for the User
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        with col_cfg1: load = st.select_slider("Traffic Intensity", ["Light", "Normal", "Heavy", "Extreme"], value="Heavy")
        with col_cfg2: speed = st.select_slider("Simulation Speed", ["Normal", "Fast"], value="Fast")
        with col_cfg3: 
            st.write("") # Spacer
            start_btn = st.button("▶️ Start Live Comparison", type="primary", use_container_width=True)

    # --- THE LIVE DEMO ---
    if start_btn:
        st.divider()
        
        # Map "Sales" terms to Technical Values
        load_map = {"Light": 0.5, "Normal": 1.0, "Heavy": 1.2, "Extreme": 1.5}
        
        # Init Parallel Models
        cfg = {"traffic_multiplier": load_map[load]}
        fifo = ChargingStationModel(4, "FIFO", seed=42, user_config=cfg)
        sirq = ChargingStationModel(4, "SIRQ", seed=42, user_config=cfg)
        
        # Layout: Side-by-Side
        c_fifo, c_sirq = st.columns(2)
        
        with c_fifo: 
            st.markdown("### ❌ Legacy Operations (FIFO)")
            st.markdown("**First-In, First-Out.** Watch how 🔴 VIPs get blocked by ⚪ Economy trucks.")
            ph_fifo = st.empty()
            metric_fifo = st.empty()
            
        with c_sirq: 
            st.markdown("### ✅ SIRQ Smart Operations")
            st.markdown("**Dynamic Priority.** Watch how 🔴 VIPs jump to the front immediately.")
            ph_sirq = st.empty()
            metric_sirq = st.empty()
            
        bar = st.progress(0)
        
        # Parallel Loop
        skip = 5 if speed == "Normal" else 20
        sleep = 0.05 if speed == "Normal" else 0.001
        
        for i in range(1440): # 24 Hours
            fifo.step()
            sirq.step()
            
            if i % skip == 0:
                bar.progress((i+1)/1440)
                
                # Render Visuals
                ph_fifo.markdown(render_station_visual(fifo), unsafe_allow_html=True)
                ph_sirq.markdown(render_station_visual(sirq), unsafe_allow_html=True)
                
                # Render Business Metrics (Not just raw stats)
                metric_fifo.error(f"""
                **Revenue:** ${int(fifo.kpi_revenue)}
                \n**VIP Failures:** {fifo.kpi_failed_critical}
                """)
                
                metric_sirq.success(f"""
                **Revenue:** ${int(sirq.kpi_revenue)}
                \n**VIP Failures:** {sirq.kpi_failed_critical}
                """)
                
                time.sleep(sleep)
        
        st.success("Simulation Complete. Notice the Revenue Uplift and VIP Protection in the SIRQ panel.")

# =========================================================
# PAGE 2: MONTE CARLO EXECUTION
# =========================================================
elif page == "2. Monte Carlo Simulation":
    st.title("⚡ Scientific Validation")
    st.markdown("To prove the results aren't just luck, we run **N** simulations.")
    
    with st.form("mc_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_runs = st.number_input("Iterations (N)", 30, 200, 50)
            loads = st.multiselect("Traffic Scenarios", [0.5, 0.8, 1.0, 1.2, 1.5, 2.0], default=[0.8, 1.0, 1.2, 1.5])
        with c2:
            st.markdown("Traffic Mix:")
            pc = st.slider("VIP %", 0.0, 1.0, 0.2)
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
elif page == "3. Analytics":
    st.title("📊 Deep Dive on the Data")
    
    df = st.session_state['monte_carlo_df']
    if df is None:
        st.warning("No Data. Run Monte Carlo first.")
    else:
        plotter = ScientificPlotter(df)
        tab1, tab2, tab3 = st.tabs(["RQ1: Revenue Efficiency", "RQ2: VIP Reliability", "RQ3: Equity Cost"])
        
        with tab1:
            st.header("RQ1: Revenue Impact")
            st.markdown("Does the auction mechanism significantly increase daily turnover?")
            st.plotly_chart(plotter.rq1_revenue_ci(), use_container_width=True)
            with st.expander("Show Distribution & Delta"):
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plotter.rq1_revenue_dist(), use_container_width=True)
                with c2: 
                    d_fig = plotter.rq1_revenue_delta()
                    if d_fig: st.plotly_chart(d_fig, use_container_width=True)

        with tab2:
            st.header("RQ2: VIP Service Level")
            st.markdown("Are we successfully protecting the Critical Supply Chain?")
            st.plotly_chart(plotter.rq2_critical_wait_box(), use_container_width=True)
            with st.expander("Show Failure Rates & ECDF"):
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plotter.rq2_failure_rate(), use_container_width=True)
                with c2: st.plotly_chart(plotter.rq2_ecdf_wait(), use_container_width=True)

        with tab3:
            st.header("RQ3: Equity & Starvation")
            st.markdown("How much do Economy drivers suffer to subsidize VIPs?")
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
        st.subheader("Export")
        if st.session_state['monte_carlo_df'] is not None:
            csv = st.session_state['monte_carlo_df'].to_csv(index=False).encode('utf-8')
            st.download_button("Download .csv", csv, "sirq_results.csv", "text/csv")
    with c2:
        st.subheader("Import")
        f = st.file_uploader("Upload CSV", type="csv")
        if f:
            st.session_state['monte_carlo_df'] = pd.read_csv(f)
            st.success("Loaded!")