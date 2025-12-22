import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import numpy as np
from src.model import ChargingStationModel
from src.utils import create_experiment_zip, load_experiment_zip

st.set_page_config(layout="wide", page_title="SIRQ Research Platform")

# --- SHARED FUNCTIONS ---
def run_single_step(model):
    model.step()
    return model

def render_station_visual(model, title_color):
    # (Keep previous visualization logic exactly as is - shortened here for brevity)
    chargers = [a for a in model.schedule.agents if a.status == "Charging"]
    queue = [a for a in model.schedule.agents if a.status == "Queuing"]
    if model.strategy == "FIFO": queue.sort(key=lambda x: x.unique_id)
    else: queue.sort(key=lambda x: x.bid, reverse=True)
    
    charger_html = ""
    for i in range(model.num_chargers):
        if i < len(chargers):
            truck = chargers[i]
            charger_html += f"""<div style="background-color: {truck.color}; color: white; padding: 6px; border-radius: 6px; width: 90px; text-align: center; border: {truck.border}; margin: 3px; box-shadow: 1px 1px 3px rgba(0,0,0,0.2);"><div style="font-size: 14px; font-weight: bold;">⚡ {i+1}</div><div style="font-size: 12px; font-weight: bold;">${int(truck.bid)}</div><div style="font-size: 9px; opacity: 0.9;">{truck.profile_type[0]}</div></div>"""
        else:
            charger_html += f"""<div style="background-color: #f0f2f6; color: #bcccdb; padding: 6px; border-radius: 6px; width: 90px; text-align: center; border: 2px dashed #dbe4eb; margin: 3px;"><div style="font-size: 14px;">💤 {i+1}</div></div>"""
    queue_html = ""
    if not queue: queue_html = "<div style='color: #aaa; font-style: italic; font-size: 12px; padding: 5px;'>Queue is Empty</div>"
    else:
        for truck in queue[:12]:
            queue_html += f"""<div style="background-color: {truck.color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-align: center; margin: 2px; min-width: 45px; border: {truck.border};" title="ID: {truck.unique_id} | {truck.profile_type}"><div style="font-weight: bold;">${int(truck.bid)}</div></div>"""
        if len(queue) > 12: queue_html += f"<div style='color: #888; font-size: 10px;'>+{len(queue)-12} more</div>"

    return f"""<div style="font-family: sans-serif;"><div style="display: flex; flex-wrap: wrap; margin-bottom: 5px;">{charger_html}</div><div style="background-color: #f8f9fa; padding: 8px; border-radius: 8px; border-left: 4px solid #ddd; display: flex; flex-wrap: wrap;">{queue_html}</div></div>""".replace("\n", "").strip()

# --- INIT STATE ---
if 'monte_carlo_results' not in st.session_state: st.session_state['monte_carlo_results'] = None
if 'single_run_data' not in st.session_state: st.session_state['single_run_data'] = None

# --- SIDEBAR ---
st.sidebar.title("🔬 SIRQ Research")
page = st.sidebar.radio("Mode Selection", ["1. Monte Carlo Laboratory", "2. Visual Deep Dive", "3. Data Manager"])

# ==========================================
# PAGE 1: MONTE CARLO LABORATORY (HOME)
# ==========================================
if page == "1. Monte Carlo Laboratory":
    st.title("🎲 Monte Carlo Laboratory")
    st.markdown("""
    **Objective:** Prove statistical significance by running the experiment $N$ times.
    
    
    
    This tool runs a **Parameter Sweep** across different Traffic Loads (Sensitivity Analysis) to see where FIFO fails and SIRQ succeeds.
    """)
    
    # 1. SETUP
    with st.expander("🛠️ Experiment Configuration", expanded=True):
        with st.form("monte_carlo_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                n_runs = st.number_input("Iterations per Config (N)", 30, 500, 50, help="Higher is better for journals. N=50 is standard.")
                chargers = st.number_input("Number of Chargers", 2, 10, 4)
            with c2:
                # Sensitivity Analysis Parameters
                traffic_multipliers = st.multiselect("Traffic Loads to Test", [0.5, 0.8, 1.0, 1.2, 1.5, 2.0], default=[0.8, 1.0, 1.2, 1.5])
                strategies = st.multiselect("Strategies", ["FIFO", "SIRQ"], default=["FIFO", "SIRQ"])
            with c3:
                # Profile Config
                st.markdown("**Profile Weights:**")
                p_crit = st.slider("Critical %", 0, 100, 20) / 100
                p_std = st.slider("Standard %", 0, 100, 60) / 100
                p_eco = st.slider("Economy %", 0, 100, 20) / 100
            
            run_mc = st.form_submit_button("🚀 Run Monte Carlo Simulation")

    # 2. EXECUTION
    if run_mc:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_steps = len(traffic_multipliers) * len(strategies) * n_runs
        current_step = 0
        
        # Define user config for the model
        base_config = {
            "prob_critical": p_crit, "prob_standard": p_std, "prob_economy": p_eco,
            "charger_power": 150.0, "price_per_kwh": 0.5
        }

        start_time = time.time()
        
        for load in traffic_multipliers:
            for strat in strategies:
                for i in range(n_runs):
                    # Unique seed for every single run
                    seed = np.random.randint(10000, 99999)
                    
                    # Update config with current load
                    run_config = base_config.copy()
                    run_config["traffic_multiplier"] = load
                    
                    # Init Model
                    model = ChargingStationModel(chargers, strategy=strat, seed=seed, user_config=run_config)
                    
                    # Run Full Day (1440 mins) - Optimized loop
                    for _ in range(1440):
                        model.step()
                    
                    # Collect Metrics
                    crit_wait = pd.DataFrame(model.agent_log).query("Profile=='CRITICAL'")['Wait_Time'].mean()
                    
                    results.append({
                        "Traffic_Load": load,
                        "Strategy": strat,
                        "Run_ID": i,
                        "Revenue": model.kpi_revenue,
                        "Critical_Failures": model.kpi_failed_critical,
                        "Avg_Wait_Critical": 0 if np.isnan(crit_wait) else crit_wait,
                        "Total_Preemptions": model.kpi_preemptions
                    })
                    
                    current_step += 1
                    if current_step % 5 == 0: # Update UI every 5 steps to save time
                        progress_bar.progress(current_step / total_steps)
                        status_text.text(f"Simulating... {current_step}/{total_steps} runs completed.")

        elapsed = time.time() - start_time
        status_text.success(f"Simulation Complete! Processed {total_steps} runs in {elapsed:.1f} seconds.")
        st.session_state['monte_carlo_results'] = pd.DataFrame(results)

    # 3. ANALYSIS
    if st.session_state['monte_carlo_results'] is not None:
        df = st.session_state['monte_carlo_results']
        
        st.divider()
        st.header("📊 Monte Carlo Results Analysis")
        
        tab1, tab2, tab3 = st.tabs(["💰 Revenue Robustness", "⚠️ Reliability (Failures)", "⏱️ Critical Service Level"])
        
        with tab1:
            st.markdown("**Hypothesis:** SIRQ maintains higher revenue stability as traffic increases.")
            # Aggregation for Error Bars
            summary = df.groupby(["Traffic_Load", "Strategy"])["Revenue"].agg(["mean", "std", "count"]).reset_index()
            summary['ci95'] = 1.96 * (summary['std'] / np.sqrt(summary['count'])) # 95% Confidence Interval formula
            
            fig = go.Figure()
            for s in strategies:
                sub = summary[summary["Strategy"] == s]
                fig.add_trace(go.Scatter(
                    x=sub["Traffic_Load"], y=sub["mean"],
                    error_y=dict(type='data', array=sub['ci95'], visible=True),
                    mode='lines+markers', name=s
                ))
            fig.update_layout(title="Mean Revenue with 95% Confidence Intervals", xaxis_title="Traffic Multiplier", yaxis_title="Daily Revenue ($)")
            st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            st.markdown("**Hypothesis:** SIRQ prevents system collapse (Critical Failures) under heavy load.")
            # Box plot shows the distribution across the N runs
            fig_fail = px.box(df, x="Traffic_Load", y="Critical_Failures", color="Strategy", 
                              title="Distribution of Critical Failures (N Runs)")
            st.plotly_chart(fig_fail, use_container_width=True)
            
        with tab3:
            st.markdown("**Hypothesis:** Critical Trucks wait near zero minutes in SIRQ, regardless of load.")
            fig_wait = px.box(df, x="Traffic_Load", y="Avg_Wait_Critical", color="Strategy",
                              title="Avg Wait Time for Critical Trucks")
            st.plotly_chart(fig_wait, use_container_width=True)

        # Download Full Dataset
        st.download_button("💾 Download Monte Carlo Dataset (.csv)", df.to_csv(index=False).encode('utf-8'), "monte_carlo_results.csv", "text/csv")


# ==========================================
# PAGE 2: VISUAL DEEP DIVE (SINGLE RUN)
# ==========================================
elif page == "2. Visual Deep Dive":
    st.title("🎥 Visual Deep Dive")
    st.markdown("Use this tab to observe the **micro-dynamics** of a single day. This helps explain *why* the Monte Carlo stats look the way they do.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Single Run Config")
        s_strat = st.selectbox("Strategy", ["FIFO", "SIRQ"])
        s_load = st.selectbox("Traffic Load", [0.8, 1.0, 1.2, 1.5])
        s_seed = st.number_input("Seed", value=42)
        s_speed = st.select_slider("Speed", ["Instant", "Fast", "Normal", "Slow"], value="Fast")
        
        btn_visual = st.button("Run Visualizer")

    if btn_visual:
        user_config = {
            "traffic_multiplier": s_load,
            "prob_critical": 0.2, "prob_standard": 0.6, "prob_economy": 0.2, # defaults
            "charger_power": 150.0, "price_per_kwh": 0.5
        }
        
        model = ChargingStationModel(4, strategy=s_strat, seed=s_seed, user_config=user_config)
        
        placeholder_vis = st.empty()
        placeholder_stats = st.empty()
        progress = st.progress(0)
        
        refresh_map = {"Instant": 1440, "Fast": 20, "Normal": 5, "Slow": 1}
        sleep_map = {"Instant": 0, "Fast": 0.001, "Normal": 0.05, "Slow": 0.2}

        # Live Loop
        for step in range(1440):
            model.step()
            
            if step % refresh_map[s_speed] == 0:
                progress.progress((step+1)/1440)
                placeholder_vis.markdown(render_station_visual(model, "blue"), unsafe_allow_html=True)
                placeholder_stats.info(f"Step: {step} | Rev: ${int(model.kpi_revenue)} | Failures: {model.kpi_failed_critical}")
                if s_speed != "Instant": time.sleep(sleep_map[s_speed])
        
        st.success("Run Complete.")
        
        # Show Detailed Logs for this specific run
        df_log = pd.DataFrame(model.agent_log)
        st.subheader("Agent Log (Single Run)")
        st.dataframe(df_log)


# ==========================================
# PAGE 3: DATA MANAGER
# ==========================================
elif page == "3. Data Manager":
    st.title("💾 Data Manager")
    st.write("Upload/Download logic remains here.")
    # (Reuse previous logic here if needed, or keep simple)