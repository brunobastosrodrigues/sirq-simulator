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
if page == "1. Business Value Demo":
    st.title("🚛 Stop Losing Revenue to Inefficient Queues")
    st.markdown("""
    **The Problem:** In FIFO, high-value trucks ($100 bid) get stuck behind low-value traffic ($20 bid). 
    **The Solution:** SIRQ uses an auction to prioritize high-value logistics automatically. 
    """)
    
    st.divider()

    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Drivers")
        st.info("🔴 **VIP (Critical)**: Pays 5x, Can't Wait")
        st.info("🔵 **Standard**: Normal urgency")
        st.info("⚪ **Economy**: Low pay, Can wait")

    with c2:
        st.subheader("⚡ Live Digital Twin")
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        with col_cfg1: load = st.select_slider("Traffic", ["Normal", "Heavy", "Extreme"], value="Heavy")
        with col_cfg2: speed = st.select_slider("Speed", ["Normal", "Fast"], value="Fast")
        with col_cfg3: 
            st.write("")
            start_btn = st.button("▶️ Start Comparison", type="primary", use_container_width=True)

    if start_btn:
        st.divider()
        load_map = {"Normal": 1.0, "Heavy": 1.2, "Extreme": 1.5}
        
        # Parallel Execution
        cfg = {"traffic_multiplier": load_map[load]}
        fifo = ChargingStationModel(4, "FIFO", seed=42, user_config=cfg)
        sirq = ChargingStationModel(4, "SIRQ", seed=42, user_config=cfg)
        
        c_fifo, c_sirq = st.columns(2)
        with c_fifo: 
            st.markdown("### ❌ Legacy (FIFO)")
            ph_fifo = st.empty()
            metric_fifo = st.empty()
        with c_sirq: 
            st.markdown("### ✅ SIRQ (Smart)")
            ph_sirq = st.empty()
            metric_sirq = st.empty()
            
        bar = st.progress(0)
        skip = 5 if speed == "Normal" else 20
        sleep = 0.05 if speed == "Normal" else 0.001
        
        for i in range(1440):
            fifo.step()
            sirq.step()
            
            if i % skip == 0:
                bar.progress((i+1)/1440)
                ph_fifo.markdown(render_station_visual(fifo), unsafe_allow_html=True)
                ph_sirq.markdown(render_station_visual(sirq), unsafe_allow_html=True)
                
                metric_fifo.error(f"**Rev:** ${int(fifo.kpi_revenue)} | **VIP Fail:** {fifo.kpi_failed_critical}")
                metric_sirq.success(f"**Rev:** ${int(sirq.kpi_revenue)} | **VIP Fail:** {sirq.kpi_failed_critical}")
                time.sleep(sleep)
        st.success("Simulation Complete.")

# =========================================================
# PAGE 2: MONTE CARLO EXECUTION
# =========================================================
elif page == "2. Scientific Simulation (Lab)":
    st.title("⚡ Scientific Validation")
    st.markdown("Run **N** simulations to generate statistically significant data for the analytics module.")
    
    with st.form("mc_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_runs = st.number_input("N (Runs/Config)", 30, 200, 30)
            loads = st.multiselect("Traffic", [0.8, 1.0, 1.2, 1.5], default=[1.0, 1.2, 1.5])
        with c2:
            st.markdown("Profile Mix:")
            pc = st.slider("VIP %", 0.0, 1.0, 0.2)
            ps = st.slider("Standard %", 0.0, 1.0, 0.6)
            pe = st.slider("Economy %", 0.0, 1.0, 0.2)
        
        run_btn = st.form_submit_button("🚀 Run Batch")
        
    if run_btn:
        results = []
        prog = st.progress(0)
        stat = st.empty()
        total = len(loads) * 2 * n_runs
        curr = 0
        
        base = {"prob_critical": pc, "prob_standard": ps, "prob_economy": pe}
        
        for l in loads:
            for s in ["FIFO", "SIRQ"]:
                for i in range(n_runs):
                    seed = np.random.randint(100000, 999999)
                    cfg = base.copy(); cfg["traffic_multiplier"] = l
                    m = ChargingStationModel(4, s, seed=seed, user_config=cfg)
                    for _ in range(1440): m.step()
                    
                    df_log = pd.DataFrame(m.agent_log)
                    cw = df_log.query("Profile=='CRITICAL'")['Wait_Time'].mean() if not df_log.empty else 0
                    ew = df_log.query("Profile=='ECONOMY'")['Wait_Time'].mean() if not df_log.empty else 0
                    
                    results.append({
                        "Run_ID": i, "Traffic_Load": l, "Strategy": s,
                        "Revenue": m.kpi_revenue, "Critical_Failures": m.kpi_failed_critical,
                        "Avg_Wait_Critical": cw, "Avg_Wait_Economy": ew
                    })
                    curr += 1
                    if curr % 10 == 0:
                        prog.progress(curr/total)
                        stat.text(f"Processing... {curr}/{total}")
                        
        st.session_state['monte_carlo_df'] = pd.DataFrame(results)
        st.success("Batch Complete. Go to 'Deep Dive Analytics'.")

# =========================================================
# PAGE 3: DEEP DIVE ANALYTICS
# =========================================================
elif page == "3. Deep Dive Analytics":
    st.title("📊 Scientific Analytics")
    df = st.session_state['monte_carlo_df']
    
    if df is None:
        st.warning("No Data. Run Monte Carlo first.")
    else:
        plotter = ScientificPlotter(df)
        tab1, tab2, tab3 = st.tabs(["RQ1: Revenue", "RQ2: Reliability", "RQ3: Equity"])
        
        with tab1:
            st.header("RQ1: Revenue Efficiency")
            st.plotly_chart(plotter.rq1_revenue_ci(), use_container_width=True)
            with st.expander("🔎 Detailed Distributions"):
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plotter.rq1_revenue_dist(), use_container_width=True)
                with c2: 
                    d = plotter.rq1_revenue_delta()
                    if d: st.plotly_chart(d, use_container_width=True)

        with tab2:
            st.header("RQ2: VIP Reliability")
            st.plotly_chart(plotter.rq2_critical_wait_box(), use_container_width=True)
            with st.expander("🔎 Failure Analysis"):
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(plotter.rq2_failure_rate(), use_container_width=True)
                with c2: st.plotly_chart(plotter.rq2_ecdf_wait(), use_container_width=True)

        with tab3:
            st.header("RQ3: Equity Cost")
            st.plotly_chart(plotter.rq3_equity_gap(), use_container_width=True)
            with st.expander("🔎 Starvation Scatter"):
                st.plotly_chart(plotter.rq3_starvation_scatter(), use_container_width=True)

# =========================================================
# PAGE 4: DATA MANAGER
# =========================================================
elif page == "4. Data Manager":
    st.title("💾 Data Manager")
    c1, c2 = st.columns(2)
    with c1:
        if st.session_state['monte_carlo_df'] is not None:
            csv = st.session_state['monte_carlo_df'].to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "sirq_results.csv", "text/csv")
    with c2:
        f = st.file_uploader("Upload CSV", type="csv")
        if f:
            st.session_state['monte_carlo_df'] = pd.read_csv(f)
            st.success("Loaded!")