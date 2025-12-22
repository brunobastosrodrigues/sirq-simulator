import streamlit as st
import pandas as pd
import plotly.express as px
import time
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
            # Use Agent's internal color property
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
        # Default Advanced Config
        "prob_critical": 0.2, "prob_standard": 0.6, "prob_economy": 0.2,
        "charger_power": 150.0, "price_per_kwh": 0.5
    }

st.sidebar.title("🧪 SIRQ Labs")
page = st.sidebar.radio("Navigation", ["1. Run Experiment", "2. Analysis Dashboard", "3. Data Manager"])

if page == "1. Run Experiment":
    st.title("🎥 Live Visual Benchmark")
    
    with st.expander("ℹ️ Profiles & Legend", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown("🟥 **CRITICAL**<br>High Urgency, High Bid", unsafe_allow_html=True)
        with c2: st.markdown("🟦 **STANDARD**<br>Medium Urgency", unsafe_allow_html=True)
        with c3: st.markdown("⬜ **ECONOMY**<br>Low Bid, Price Sensitive", unsafe_allow_html=True)

    # --- CONFIGURATION SECTION ---
    with st.form("config_form"):
        st.subheader("1. Station Setup")
        c1, c2, c3 = st.columns(3)
        with c1: num_chargers = st.number_input("Chargers", 2, 10, value=st.session_state['experiment_config']["num_chargers"])
        with c2: seed = st.number_input("Seed", value=st.session_state['experiment_config']["seed"])
        with c3: speed = st.select_slider("Speed", ["Instant", "Fast", "Normal", "Slow"], value=st.session_state['experiment_config']["speed"])
        
        st.subheader("2. Traffic Composition (Profiles)")
        st.caption("Define the mix of truck drivers (Must sum roughly to 100%)")
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
        # Build Config Dict
        user_config = {
            "prob_critical": p_crit, "prob_standard": p_std, "prob_economy": p_eco,
            "charger_power": power, "price_per_kwh": price
        }
        # Save to Session
        full_config = {"num_chargers": num_chargers, "seed": seed, "speed": speed, **user_config}
        st.session_state['experiment_config'] = full_config
        
        # Init Models
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

        # Save
        df_agents = pd.concat([pd.DataFrame(model_fifo.agent_log), pd.DataFrame(model_sirq.agent_log)])
        df_timeline = pd.concat([pd.DataFrame(model_fifo.system_log), pd.DataFrame(model_sirq.system_log)])
        st.session_state['experiment_data'] = {"agents": df_agents, "timeline": df_timeline}

elif page == "2. Analysis Dashboard":
    st.title("📊 Scientific Analysis")
    data = st.session_state['experiment_data']
    if data:
        df_agents = data['agents']
        df_timeline = data['timeline']
        
        tab1, tab2 = st.tabs(["Efficiency", "Profile Analysis"])
        with tab1:
            fig = px.line(df_timeline, x="Step", y="Total_Revenue", color="Strategy", title="Revenue")
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            st.markdown("### How did different profiles perform?")
            # Profile Comparison
            fig = px.box(df_agents, x="Profile", y="Wait_Time", color="Strategy", 
                         title="Wait Time by Profile Type (Critical vs Economy)")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run experiment first.")

elif page == "3. Data Manager":
    st.title("💾 Data Manager")
    # (Same as before, simplified for brevity)
    if st.session_state['experiment_data']:
        zip_buffer = create_experiment_zip(st.session_state['experiment_config'], st.session_state['experiment_data']['agents'], st.session_state['experiment_data']['timeline'])
        st.download_button("Download .zip", zip_buffer, "sirq_experiment.zip", "application/zip")