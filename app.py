import streamlit as st
import pandas as pd
import plotly.express as px
import time
from src.model import ChargingStationModel
from src.utils import create_experiment_zip, load_experiment_zip

st.set_page_config(layout="wide", page_title="SIRQ Workbench")

# --- VISUALIZATION ENGINE (FLATTENED HTML FIX) ---
def render_station_visual(model, title_color):
    """
    Creates an HTML representation of the Station.
    Crucial: Flattens HTML to prevent Streamlit from rendering it as a code block.
    """
    chargers = [a for a in model.schedule.agents if a.status == "Charging"]
    queue = [a for a in model.schedule.agents if a.status == "Queuing"]
    
    if model.strategy == "FIFO":
        queue.sort(key=lambda x: x.unique_id)
    else:
        queue.sort(key=lambda x: x.bid, reverse=True)

    # --- 1. Build Charger HTML ---
    charger_html = ""
    for i in range(model.num_chargers):
        if i < len(chargers):
            truck = chargers[i]
            # Colors: Red (#ff4b4b) for Urgent, Blue (#3498db) for Normal
            color = "#ff4b4b" if truck.urgency > 0.7 else "#3498db"
            border = "3px solid #b71c1c" if truck.urgency > 0.7 else "1px solid #2980b9"
            
            charger_html += f"""
            <div style="background-color: {color}; color: white; padding: 6px; border-radius: 6px; 
                        width: 90px; text-align: center; border: {border}; margin: 3px; box-shadow: 1px 1px 3px rgba(0,0,0,0.2);">
                <div style="font-size: 14px; font-weight: bold;">⚡ {i+1}</div>
                <div style="font-size: 12px; font-weight: bold;">${int(truck.bid)}</div>
                <div style="font-size: 10px; opacity: 0.9;">SOC: {int(truck.soc)}%</div>
            </div>"""
        else:
            charger_html += f"""
            <div style="background-color: #f0f2f6; color: #bcccdb; padding: 6px; border-radius: 6px; 
                        width: 90px; text-align: center; border: 2px dashed #dbe4eb; margin: 3px;">
                <div style="font-size: 14px;">💤 {i+1}</div>
                <div style="font-size: 10px; margin-top: 5px;">Empty</div>
            </div>"""

    # --- 2. Build Queue HTML ---
    queue_html = ""
    if not queue:
        queue_html = "<div style='color: #aaa; font-style: italic; font-size: 12px; padding: 5px;'>Queue is Empty</div>"
    else:
        # Limit to first 12 trucks to prevent UI overflow
        for truck in queue[:12]:
            color = "#ff4b4b" if truck.urgency > 0.7 else "#3498db"
            border = "2px solid #b71c1c" if truck.urgency > 0.7 else "1px solid #2980b9"
            queue_html += f"""
            <div style="background-color: {color}; color: white; padding: 4px 8px; border-radius: 4px; 
                        font-size: 11px; text-align: center; margin: 2px; min-width: 45px; border: {border};" 
                        title="ID: {truck.unique_id} | Bid: ${truck.bid}">
                <div style="font-weight: bold;">${int(truck.bid)}</div>
            </div>"""
        
        if len(queue) > 12:
            queue_html += f"<div style='color: #888; font-size: 10px; padding: 5px;'>+{len(queue)-12} more</div>"

    # --- 3. Assemble & FLATTEN (The Fix) ---
    # We remove newlines to force Streamlit to treat this as raw HTML, not code
    full_html = f"""
    <div style="font-family: sans-serif; margin-bottom: 10px;">
        <div style="font-size: 12px; font-weight: bold; color: #555; margin-bottom: 5px;">CHARGING BAYS</div>
        <div style="display: flex; flex-wrap: wrap; margin-bottom: 10px;">
            {charger_html}
        </div>
        <div style="background-color: #f8f9fa; padding: 8px; border-radius: 8px; border-left: 4px solid #ddd;">
            <div style="font-size: 11px; font-weight: bold; color: #777; margin-bottom: 5px;">WAITING QUEUE (Front ➝ Back)</div>
            <div style="display: flex; flex-wrap: wrap; align-items: center;">
                {queue_html}
            </div>
        </div>
    </div>
    """
    return full_html.replace("\n", "").strip()

# --- APP LOGIC ---
if 'experiment_data' not in st.session_state:
    st.session_state['experiment_data'] = None
if 'experiment_config' not in st.session_state:
    st.session_state['experiment_config'] = {"num_chargers": 4, "seed": 42, "speed": "Fast"}

st.sidebar.title("🧪 SIRQ Labs")
page = st.sidebar.radio("Navigation", ["1. Run Experiment", "2. Analysis Dashboard", "3. Data Manager"])

# ==========================================
# PAGE 1: RUN EXPERIMENT
# ==========================================
if page == "1. Run Experiment":
    st.title("🎥 Live Visual Benchmark")
    
    # Visual Legend
    with st.expander("ℹ️ Visual Legend (Click to expand)", expanded=True):
        c1, c2 = st.columns(2)
        with c1: st.markdown("🟥 **RED Box:** High Urgency / Critical Truck (High Bid)")
        with c2: st.markdown("🟦 **BLUE Box:** Low Urgency / Standard Truck (Low Bid)")

    # Config
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        defaults = st.session_state['experiment_config']
        with c1: num_chargers = st.number_input("Chargers", 2, 8, value=defaults["num_chargers"])
        with c2: seed = st.number_input("Seed", value=defaults["seed"])
        with c3: speed = st.select_slider("Speed", ["Instant", "Fast", "Normal", "Slow"], value=defaults["speed"])

    if st.button("🏁 Start Live Race", type="primary"):
        st.session_state['experiment_config'] = {"num_chargers": num_chargers, "seed": seed, "speed": speed}
        
        # Init Models
        model_fifo = ChargingStationModel(num_chargers, strategy="FIFO", seed=seed)
        model_sirq = ChargingStationModel(num_chargers, strategy="SIRQ", seed=seed)
        
        # UI Layout
        col_fifo, col_sirq = st.columns(2)
        
        with col_fifo: 
            st.markdown("### 🔵 Baseline (FIFO)")
            st.caption("First-Come-First-Served. Note the Red trucks getting stuck.")
            fifo_vis = st.empty()
            fifo_stats = st.empty()
            
        with col_sirq: 
            st.markdown("### 🟢 SIRQ (Auction)")
            st.caption("Dynamic Priority. Note the Red trucks jumping to front.")
            sirq_vis = st.empty()
            sirq_stats = st.empty()
            
        progress = st.progress(0)
        
        # Speed Control
        refresh_map = {"Instant": 1440, "Fast": 20, "Normal": 5, "Slow": 1}
        sleep_map = {"Instant": 0, "Fast": 0.001, "Normal": 0.05, "Slow": 0.3}
        
        # --- MAIN LOOP ---
        for step in range(1440):
            model_fifo.step()
            model_sirq.step()
            
            if step % refresh_map[speed] == 0:
                progress.progress((step+1)/1440)
                
                # Render Visuals (HTML)
                fifo_vis.markdown(render_station_visual(model_fifo, "blue"), unsafe_allow_html=True)
                sirq_vis.markdown(render_station_visual(model_sirq, "green"), unsafe_allow_html=True)
                
                # Render Metrics (Text)
                fifo_stats.info(f"💰 Revenue: ${int(model_fifo.kpi_revenue)} | ⚠️ Critical Failures: {model_fifo.kpi_failed_critical}")
                sirq_stats.success(f"💰 Revenue: ${int(model_sirq.kpi_revenue)} | ⚠️ Critical Failures: {model_sirq.kpi_failed_critical}")
                
                if speed != "Instant":
                    time.sleep(sleep_map[speed])

        # Save Data
        df_agents = pd.concat([pd.DataFrame(model_fifo.agent_log), pd.DataFrame(model_sirq.agent_log)])
        df_timeline = pd.concat([pd.DataFrame(model_fifo.system_log), pd.DataFrame(model_sirq.system_log)])
        st.session_state['experiment_data'] = {"agents": df_agents, "timeline": df_timeline}
        st.success("✅ Experiment Complete! Check the Analysis Dashboard.")

# ==========================================
# PAGE 2: ANALYSIS DASHBOARD
# ==========================================
elif page == "2. Analysis Dashboard":
    st.title("📊 Scientific Analysis")
    data = st.session_state['experiment_data']
    
    if data:
        df_agents = data['agents']
        df_timeline = data['timeline']
        
        tab1, tab2, tab3 = st.tabs(["Efficiency Metrics", "Wait Time Analysis", "Queue Dynamics"])
        
        with tab1:
            st.markdown("### 💰 Revenue & Throughput")
            c1, c2 = st.columns(2)
            # Total Revenue
            rev_sum = df_timeline.groupby("Strategy")["Total_Revenue"].max().reset_index()
            fig1 = px.bar(rev_sum, x="Strategy", y="Total_Revenue", color="Strategy", title="Total Revenue ($)")
            c1.plotly_chart(fig1, use_container_width=True)
            # Growth Curve
            fig2 = px.line(df_timeline, x="Step", y="Total_Revenue", color="Strategy", title="Revenue Accumulation Over 24h")
            c2.plotly_chart(fig2, use_container_width=True)

        with tab2:
            st.markdown("### ⏱️ Wait Time Efficiency")
            st.caption("Did high-priority trucks wait less?")
            fig = px.scatter(df_agents, x="Urgency", y="Wait_Time", color="Outcome", facet_col="Strategy",
                             title="Urgency vs Wait Time (SIRQ should show a negative slope)",
                             hover_data=["ID", "Bid"])
            st.plotly_chart(fig, use_container_width=True)
            
        with tab3:
            st.markdown("### 🚧 Queue Stress")
            fig = px.area(df_timeline, x="Step", y="Queue_Length", color="Strategy", title="Queue Length Over Time")
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.info("No experiment data found. Please run an experiment first.")

# ==========================================
# PAGE 3: DATA MANAGER
# ==========================================
elif page == "3. Data Manager":
    st.title("💾 Data Manager")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Download Results")
        if st.session_state['experiment_data']:
            zip_buffer = create_experiment_zip(
                st.session_state['experiment_config'],
                st.session_state['experiment_data']['agents'],
                st.session_state['experiment_data']['timeline']
            )
            st.download_button("Download .zip", zip_buffer, "sirq_experiment.zip", "application/zip")
        else:
            st.warning("Run experiment first.")
            
    with c2:
        st.subheader("Load Previous Experiment")
        f = st.file_uploader("Upload .zip", type="zip")
        if f:
            try:
                cfg, ag, tm = load_experiment_zip(f)
                st.session_state['experiment_config'] = cfg
                st.session_state['experiment_data'] = {"agents": ag, "timeline": tm}
                st.success(f"Loaded Experiment (Seed: {cfg['seed']})")
            except Exception as e:
                st.error(f"Error loading file: {e}")
