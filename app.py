import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import numpy as np
from src.model import ChargingStationModel
from src.utils import create_experiment_zip, load_experiment_zip

st.set_page_config(layout="wide", page_title="SIRQ Workbench")

# --- VISUALIZATION ENGINE ---
def render_station_visual(model, title_color):
    chargers = [a for a in model.schedule.agents if a.status == "Charging"]
    queue = [a for a in model.schedule.agents if a.status == "Queuing"]
    
    if model.strategy == "FIFO":
        queue.sort(key=lambda x: x.unique_id)
    else:
        queue.sort(key=lambda x: x.bid, reverse=True)

    charger_html = ""
    for i in range(model.num_chargers):
        if i < len(chargers):
            truck = chargers[i]
            charger_html += f"""
            <div style="background-color: {truck.color}; color: white; padding: 6px; border-radius: 6px; 
                        width: 90px; text-align: center; border: {truck.border}; margin: 3px; box-shadow: 1px 1px 3px rgba(0,0,0,0.2);">
                <div style="font-size: 14px; font-weight: bold;">⚡ {i+1}</div>
                <div style="font-size: 12px; font-weight: bold;">${int(truck.bid)}</div>
                <div style="font-size: 9px; opacity: 0.9;">{truck.profile_type[0]}</div>
            </div>"""
        else:
            charger_html += f"""
            <div style="background-color: #f0f2f6; color: #bcccdb; padding: 6px; border-radius: 6px; 
                        width: 90px; text-align: center; border: 2px dashed #dbe4eb; margin: 3px;">
                <div style="font-size: 14px;">💤 {i+1}</div>
            </div>"""

    queue_html = ""
    if not queue:
        queue_html = "<div style='color: #aaa; font-style: italic; font-size: 12px; padding: 5px;'>Queue is Empty</div>"
    else:
        for truck in queue[:12]:
            queue_html += f"""
            <div style="background-color: {truck.color}; color: white; padding: 4px 8px; border-radius: 4px; 
                        font-size: 11px; text-align: center; margin: 2px; min-width: 45px; border: {truck.border};" 
                        title="ID: {truck.unique_id} | {truck.profile_type}">
                <div style="font-weight: bold;">${int(truck.bid)}</div>
            </div>"""
        if len(queue) > 12: queue_html += f"<div style='color: #888; font-size: 10px;'>+{len(queue)-12} more</div>"

    return f"""
    <div style="font-family: sans-serif;">
        <div style="display: flex; flex-wrap: wrap; margin-bottom: 5px;">{charger_html}</div>
        <div style="background-color: #f8f9fa; padding: 8px; border-radius: 8px; border-left: 4px solid #ddd; display: flex; flex-wrap: wrap;">
            {queue_html}
        </div>
    </div>
    """.replace("\n", "").strip()

# --- APP STATE ---
if 'experiment_data' not in st.session_state: st.session_state['experiment_data'] = None
if 'experiment_config' not in st.session_state:
    st.session_state['experiment_config'] = {
        "num_chargers": 4, "seed": 42, "speed": "Fast",
        "prob_critical": 0.2, "prob_standard": 0.6, "prob_economy": 0.2,
        "charger_power": 150.0, "price_per_kwh": 0.5
    }

st.sidebar.title("🧪 SIRQ Labs")
page = st.sidebar.radio("Navigation", [
    "1. Run Experiment", 
    "2. Analysis Dashboard", 
    "3. Data Manager", 
    "4. Sensitivity Analysis (Journal Mode)"
])

# ==========================================
# PAGE 1: RUN EXPERIMENT
# ==========================================
if page == "1. Run Experiment":
    st.title("🎥 Live Visual Benchmark")
    
    with st.expander("ℹ️ Profiles & Legend", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown("🟥 **CRITICAL**<br>High Urgency, High Bid", unsafe_allow_html=True)
        with c2: st.markdown("🟦 **STANDARD**<br>Medium Urgency", unsafe_allow_html=True)
        with c3: st.markdown("⬜ **ECONOMY**<br>Low Bid, Price Sensitive", unsafe_allow_html=True)

    with st.form("config_form"):
        st.subheader("1. Station Setup")
        c1, c2, c3 = st.columns(3)
        with c1: num_chargers = st.number_input("Chargers", 2, 10, value=st.session_state['experiment_config']["num_chargers"])
        with c2: seed = st.number_input("Seed", value=st.session_state['experiment_config']["seed"])
        with c3: speed = st.select_slider("Speed", ["Instant", "Fast", "Normal", "Slow"], value=st.session_state['experiment_config']["speed"])
        
        st.subheader("2. Traffic Composition")
        c1, c2, c3 = st.columns(3)
        with c1: p_crit = st.slider("Critical %", 0, 100, int(st.session_state['experiment_config']["prob_critical"]*100)) / 100.0
        with c2: p_std = st.slider("Standard %", 0, 100, int(st.session_state['experiment_config']["prob_standard"]*100)) / 100.0
        with c3: p_eco = st.slider("Economy %", 0, 100, int(st.session_state['experiment_config']["prob_economy"]*100)) / 100.0

        st.subheader("3. Technical Params")
        c1, c2 = st.columns(2)
        with c1: power = st.number_input("Charger Power (kW)", 50.0, 350.0, st.session_state['experiment_config']["charger_power"])
        with c2: price = st.number_input("Price ($/kWh)", 0.1, 2.0, st.session_state['experiment_config']["price_per_kwh"])
        
        submitted = st.form_submit_button("🏁 Update & Start Race", type="primary")

    if submitted:
        user_config = {
            "prob_critical": p_crit, "prob_standard": p_std, "prob_economy": p_eco,
            "charger_power": power, "price_per_kwh": price
        }
        full_config = {"num_chargers": num_chargers, "seed": seed, "speed": speed, **user_config}
        st.session_state['experiment_config'] = full_config
        
        model_fifo = ChargingStationModel(num_chargers, strategy="FIFO", seed=seed, user_config=user_config)
        model_sirq = ChargingStationModel(num_chargers, strategy="SIRQ", seed=seed, user_config=user_config)
        
        col_fifo, col_sirq = st.columns(2)
        with col_fifo: 
            st.markdown("### 🔵 Baseline (FIFO)")
            fifo_vis, fifo_stats = st.empty(), st.empty()
        with col_sirq: 
            st.markdown("### 🟢 SIRQ (Auction)")
            sirq_vis, sirq_stats = st.empty(), st.empty()
            
        progress = st.progress(0)
        refresh_map = {"Instant": 1440, "Fast": 20, "Normal": 5, "Slow": 1}
        sleep_map = {"Instant": 0, "Fast": 0.001, "Normal": 0.05, "Slow": 0.2}
        
        for step in range(1440):
            model_fifo.step()
            model_sirq.step()
            
            if step % refresh_map[speed] == 0:
                progress.progress((step+1)/1440)
                fifo_vis.markdown(render_station_visual(model_fifo, "blue"), unsafe_allow_html=True)
                sirq_vis.markdown(render_station_visual(model_sirq, "green"), unsafe_allow_html=True)
                fifo_stats.info(f"Rev: ${int(model_fifo.kpi_revenue)} | Fail: {model_fifo.kpi_failed_critical}")
                sirq_stats.success(f"Rev: ${int(model_sirq.kpi_revenue)} | Fail: {model_sirq.kpi_failed_critical}")
                if speed != "Instant": time.sleep(sleep_map[speed])

        df_agents = pd.concat([pd.DataFrame(model_fifo.agent_log), pd.DataFrame(model_sirq.agent_log)])
        df_timeline = pd.concat([pd.DataFrame(model_fifo.system_log), pd.DataFrame(model_sirq.system_log)])
        st.session_state['experiment_data'] = {"agents": df_agents, "timeline": df_timeline}

# ==========================================
# PAGE 2: SCIENTIFIC ANALYSIS
# ==========================================
elif page == "2. Analysis Dashboard":
    st.title("📊 Scientific Analysis Suite")
    
    data = st.session_state['experiment_data']
    
    if data:
        df_agents = data['agents']
        df_timeline = data['timeline']

        # SUMMARY TABLE
        st.header("0. Experimental Summary")
        summary = df_agents.groupby("Strategy").agg({
            "Wait_Time": ["mean", "std"], "Bid": "mean", "ID": "count"
        }).round(2)
        failures = df_agents[df_agents["Outcome"].isin(["Left (Impatient)", "Preempted"])]
        fail_counts = failures.groupby("Strategy")["ID"].count()
        rev = df_timeline.groupby("Strategy")["Total_Revenue"].max()
        
        kpi_table = pd.DataFrame({
            "Total Revenue ($)": rev,
            "Avg Wait (min)": summary[("Wait_Time", "mean")],
            "Std Dev Wait": summary[("Wait_Time", "std")],
            "Trucks Serviced": summary[("ID", "count")],
            "Failures/Preemptions": fail_counts
        })
        st.table(kpi_table)

        tab1, tab2, tab3, tab4 = st.tabs(["RQ1: Efficiency", "RQ2: Critical Priority", "RQ3: Equity", "RQ4: Congestion"])

        with tab1:
            st.markdown("### RQ1: System Efficiency")
            c1, c2 = st.columns(2)
            with c1:
                fig_rev = px.line(df_timeline, x="Step", y="Total_Revenue", color="Strategy", title="Revenue Growth ($)",
                                  color_discrete_map={"FIFO": "blue", "SIRQ": "green"})
                st.plotly_chart(fig_rev, use_container_width=True)
            with c2:
                fig_q = px.histogram(df_timeline, x="Queue_Length", color="Strategy", barmode="overlay", title="Queue Distribution", opacity=0.6)
                st.plotly_chart(fig_q, use_container_width=True)

        with tab2:
            st.markdown("### RQ2: Service Levels for Critical Profiles")
            crit_df = df_agents[df_agents["Profile"] == "CRITICAL"]
            c1, c2 = st.columns(2)
            with c1:
                fig_vio = px.violin(crit_df, y="Wait_Time", x="Strategy", color="Strategy", box=True, points="all",
                                    title="Wait Time (CRITICAL Only)", color_discrete_map={"FIFO": "blue", "SIRQ": "green"})
                st.plotly_chart(fig_vio, use_container_width=True)
            with c2:
                crit_fail = crit_df[crit_df["Outcome"] == "Left (Impatient)"].groupby("Strategy").size().reset_index(name="Failures")
                if not crit_fail.empty:
                    fig_fail = px.bar(crit_fail, x="Strategy", y="Failures", color="Strategy", title="Critical Failures")
                    st.plotly_chart(fig_fail, use_container_width=True)
                else:
                    st.success("No Critical Failures observed!")

        with tab3:
            st.markdown("### RQ3: Equity & Trade-offs")
            fig_box = px.box(df_agents, x="Profile", y="Wait_Time", color="Strategy", title="Wait Time by Profile (Starvation Check)",
                             category_orders={"Profile": ["CRITICAL", "STANDARD", "ECONOMY"]}, color_discrete_map={"FIFO": "blue", "SIRQ": "green"})
            st.plotly_chart(fig_box, use_container_width=True)

        with tab4:
            st.markdown("### RQ4: Congestion Dynamics")
            fig_scatter = px.scatter(df_agents, x="ID", y="Wait_Time", color="Profile", facet_col="Strategy", title="Wait Times Trend", opacity=0.5)
            st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No data. Run an experiment first.")

# ==========================================
# PAGE 3: DATA MANAGER
# ==========================================
elif page == "3. Data Manager":
    st.title("💾 Data Manager")
    c1, c2 = st.columns(2)
    with c1:
        if st.session_state['experiment_data']:
            zip_buffer = create_experiment_zip(st.session_state['experiment_config'], st.session_state['experiment_data']['agents'], st.session_state['experiment_data']['timeline'])
            st.download_button("Download .zip", zip_buffer, "sirq_experiment.zip", "application/zip")
    with c2:
        f = st.file_uploader("Upload .zip", type="zip")
        if f:
            try:
                cfg, ag, tm = load_experiment_zip(f)
                st.session_state['experiment_config'] = cfg
                st.session_state['experiment_data'] = {"agents": ag, "timeline": tm}
                st.success("Loaded!")
            except: st.error("Invalid file.")

# ==========================================
# PAGE 4: SENSITIVITY ANALYSIS (JOURNAL MODE)
# ==========================================
elif page == "4. Sensitivity Analysis (Journal Mode)":
    st.title("🔬 Sensitivity & Robustness (N=30)")
    st.markdown("Addresses the 'N=1' problem by running batch simulations with error bars.")
    
    with st.form("batch_config"):
        c1, c2 = st.columns(2)
        with c1:
            num_runs = st.number_input("Runs per Config", 10, 100, 30)
            traffic_levels = st.multiselect("Traffic Load Multipliers", [0.5, 0.8, 1.0, 1.2, 1.5, 2.0], default=[0.8, 1.0, 1.2, 1.5])
        with c2:
            strategies = st.multiselect("Strategies", ["FIFO", "SIRQ"], default=["FIFO", "SIRQ"])
            chargers_fixed = st.number_input("Fixed Chargers", 2, 8, 4)
        run_batch = st.form_submit_button("🚀 Run Batch Experiment")

    if run_batch:
        results = []
        progress = st.progress(0)
        status = st.empty()
        total = len(traffic_levels) * len(strategies) * num_runs
        curr = 0
        
        for load in traffic_levels:
            for strat in strategies:
                for i in range(num_runs):
                    model = ChargingStationModel(chargers_fixed, strategy=strat, seed=np.random.randint(1000, 99999), user_config={"traffic_multiplier": load})
                    for _ in range(1440): model.step()
                    
                    results.append({
                        "Load": load, "Strategy": strat, "Revenue": model.kpi_revenue,
                        "Failures": model.kpi_failed_critical
                    })
                    curr += 1
                    progress.progress(curr / total)
                    status.text(f"Simulating: Load {load}x | {strat} | Run {i+1}/{num_runs}")

        df_res = pd.DataFrame(results)
        st.success("Batch Complete!")
        
        tab1, tab2 = st.tabs(["Revenue Confidence", "Failure Robustness"])
        with tab1:
            summary = df_res.groupby(["Load", "Strategy"])["Revenue"].agg(["mean", "std", "count"]).reset_index()
            summary['ci'] = 1.96 * (summary['std'] / np.sqrt(summary['count']))
            
            fig = go.Figure()
            for s in strategies:
                sub = summary[summary["Strategy"] == s]
                fig.add_trace(go.Scatter(x=sub["Load"], y=sub["mean"], error_y=dict(type='data', array=sub['ci'], visible=True), mode='lines+markers', name=s))
            fig.update_layout(title="Revenue vs Traffic Load (95% CI)", xaxis_title="Load Multiplier", yaxis_title="Revenue ($)")
            st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            fig_fail = px.box(df_res, x="Load", y="Failures", color="Strategy", title="Critical Failures Distribution")
            st.plotly_chart(fig_fail, use_container_width=True)
            
        st.download_button("Download Batch CSV", df_res.to_csv(index=False).encode('utf-8'), "batch_results.csv", "text/csv")