import streamlit as st
import pandas as pd
import plotly.express as px
import time
from src.model import ChargingStationModel
from src.utils import create_experiment_zip, load_experiment_zip

# --- Page Config ---
st.set_page_config(layout="wide", page_title="SIRQ Workbench")

# --- Initialize Session State ---
if 'experiment_data' not in st.session_state:
    st.session_state['experiment_data'] = None # Stores the results (DFs)
if 'experiment_config' not in st.session_state:
    st.session_state['experiment_config'] = {  # Stores parameters
        "num_chargers": 4,
        "seed": 42,
        "speed": "Fast"
    }

# --- Sidebar Navigation ---
st.sidebar.title("🧪 SIRQ Labs")
page = st.sidebar.radio("Navigation", ["1. Run Experiment", "2. Analysis Dashboard", "3. Data Manager"])

# ==========================================
# PAGE 1: RUN EXPERIMENT
# ==========================================
if page == "1. Run Experiment":
    st.title("🚀 Experiment Runner")
    st.markdown("Configure and execute a paired benchmark (FIFO vs SIRQ).")
    
    # 1. Configuration Form
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        
        # Load defaults from session state (allows "Tweak and Rerun")
        defaults = st.session_state['experiment_config']
        
        with c1:
            num_chargers = st.number_input("Number of Chargers", 2, 10, value=defaults["num_chargers"])
        with c2:
            seed = st.number_input("Random Seed (Reproducibility)", value=defaults["seed"])
        with c3:
            speed = st.select_slider("Visual Speed", options=["Instant", "Fast", "Normal"], value=defaults["speed"])

    start_btn = st.button("🏁 Start New Benchmark", type="primary")

    if start_btn:
        # Save config to session for later export
        st.session_state['experiment_config'] = {"num_chargers": num_chargers, "seed": seed, "speed": speed}
        
        # Speed logic
        sleep_map = {"Instant": 0, "Fast": 0.001, "Normal": 0.05}
        refresh_rate_map = {"Instant": 1440, "Fast": 20, "Normal": 5}
        
        # Initialize Models
        model_fifo = ChargingStationModel(num_chargers, strategy="FIFO", seed=seed)
        model_sirq = ChargingStationModel(num_chargers, strategy="SIRQ", seed=seed)
        
        # UI Setup
        col_fifo, col_sirq = st.columns(2)
        with col_fifo:
            st.markdown("### FIFO (Baseline)")
            fifo_metric = st.empty()
            fifo_chart = st.empty()
        with col_sirq:
            st.markdown("### SIRQ (Auction)")
            sirq_metric = st.empty()
            sirq_chart = st.empty()
            
        progress = st.progress(0)
        
        # Live Loop
        live_fifo, live_sirq = [], []
        
        for step in range(1440):
            model_fifo.step()
            model_sirq.step()
            
            if step % refresh_rate_map[speed] == 0:
                progress.progress((step+1)/1440)
                
                # Update Metrics
                fifo_metric.metric("Revenue", f"${int(model_fifo.kpi_revenue)}")
                sirq_metric.metric("Revenue", f"${int(model_sirq.kpi_revenue)}", 
                                   delta=f"{int(model_sirq.kpi_revenue - model_fifo.kpi_revenue)}")
                
                # Update Charts
                live_fifo.append({"Step": step, "Queue": len([a for a in model_fifo.schedule.agents if a.status == 'Queuing'])})
                live_sirq.append({"Step": step, "Queue": len([a for a in model_sirq.schedule.agents if a.status == 'Queuing'])})
                
                if step % 50 == 0 and speed != "Instant":
                    fifo_chart.line_chart(pd.DataFrame(live_fifo).set_index("Step"), height=150)
                    sirq_chart.line_chart(pd.DataFrame(live_sirq).set_index("Step"), height=150)
                    time.sleep(sleep_map[speed])

        # --- DATA AGGREGATION & STORAGE ---
        # 1. Merge Agent Logs
        df_ag_fifo = pd.DataFrame(model_fifo.agent_log)
        df_ag_sirq = pd.DataFrame(model_sirq.agent_log)
        df_agents = pd.concat([df_ag_fifo, df_ag_sirq])
        
        # 2. Merge System Logs
        df_sys_fifo = pd.DataFrame(model_fifo.system_log)
        df_sys_sirq = pd.DataFrame(model_sirq.system_log)
        df_timeline = pd.concat([df_sys_fifo, df_sys_sirq])
        
        # 3. Store in Session State
        st.session_state['experiment_data'] = {
            "agents": df_agents,
            "timeline": df_timeline
        }
        
        st.success("Experiment Completed! Go to 'Analysis Dashboard' to view results.")

# ==========================================
# PAGE 2: ANALYSIS DASHBOARD
# ==========================================
elif page == "2. Analysis Dashboard":
    st.title("📊 Scientific Analysis")
    
    data = st.session_state['experiment_data']
    
    if data is None:
        st.warning("No experiment data found. Please run an experiment or load a file first.")
    else:
        df_agents = data['agents']
        df_timeline = data['timeline']
        config = st.session_state['experiment_config']
        
        st.caption(f"Showing results for: {config['num_chargers']} Chargers | Seed: {config['seed']}")
        
        # --- TABBED ANALYSIS ---
        tab1, tab2, tab3 = st.tabs(["📈 Efficiency & Revenue", "⏱️ Wait Times", "⚖️ Fairness & Ethics"])
        
        with tab1:
            st.markdown("### RQ1: Did SIRQ improve turnover?")
            c1, c2 = st.columns(2)
            
            # Revenue Comparison
            rev_data = df_timeline.groupby("Strategy")["Total_Revenue"].max().reset_index()
            fig_rev = px.bar(rev_data, x="Strategy", y="Total_Revenue", color="Strategy", 
                             title="Total Revenue Generated ($)", text_auto=True)
            c1.plotly_chart(fig_rev, use_container_width=True)
            
            # Throughput Over Time
            fig_line = px.line(df_timeline, x="Step", y="Total_Revenue", color="Strategy",
                               title="Cumulative Revenue Growth (24h)")
            c2.plotly_chart(fig_line, use_container_width=True)

        with tab2:
            st.markdown("### RQ2: Did critical trucks wait less?")
            
            # Filter High Urgency
            critical = df_agents[df_agents['Urgency'] > 0.7]
            
            c1, c2 = st.columns(2)
            fig_box = px.box(critical, x="Strategy", y="Wait_Time", color="Strategy",
                             title="Wait Time Distribution (Critical Trucks Only)")
            c1.plotly_chart(fig_box, use_container_width=True)
            
            # Failure Rate
            failures = critical[critical['Outcome'] == 'Left (Impatient)'].groupby("Strategy").size().reset_index(name="Failures")
            if not failures.empty:
                fig_fail = px.bar(failures, x="Strategy", y="Failures", color="Strategy",
                                  title="Number of Critical Delivery Failures")
                c2.plotly_chart(fig_fail, use_container_width=True)
            else:
                c2.success("No critical failures occurred in this run!")

        with tab3:
            st.markdown("### RQ3: Is the system fair?")
            st.markdown("This scatter plot visualizes the **Preemption Logic**. In SIRQ (right), higher urgency should correlate with lower wait times.")
            
            fig_scatter = px.scatter(df_agents, x="Urgency", y="Wait_Time", color="Outcome", 
                                     facet_col="Strategy", size="Bid", hover_data=["ID"],
                                     title="Urgency vs Wait Time (The 'Fairness Slope')")
            # Add reference line
            fig_scatter.add_hline(y=90, line_dash="dot", annotation_text="Patience Limit")
            st.plotly_chart(fig_scatter, use_container_width=True)

# ==========================================
# PAGE 3: DATA MANAGER (LOAD/SAVE)
# ==========================================
elif page == "3. Data Manager":
    st.title("💾 Data Manager")
    st.markdown("Save your experiment for publication reproducibility or load a previous run to tweak parameters.")
    
    col1, col2 = st.columns(2)
    
    # --- SAVE SECTION ---
    with col1:
        st.subheader("Download Experiment")
        if st.session_state['experiment_data'] is None:
            st.warning("No data to save. Run an experiment first.")
        else:
            st.success("Experiment data is ready.")
            
            # Generate ZIP
            zip_buffer = create_experiment_zip(
                st.session_state['experiment_config'],
                st.session_state['experiment_data']['agents'],
                st.session_state['experiment_data']['timeline']
            )
            
            st.download_button(
                label="📥 Download Full Experiment (.zip)",
                data=zip_buffer,
                file_name=f"sirq_experiment_seed{st.session_state['experiment_config']['seed']}.zip",
                mime="application/zip",
                help="Contains config.json, agents.csv, and timeline.csv"
            )

    # --- LOAD SECTION ---
    with col2:
        st.subheader("Load Experiment")
        uploaded_file = st.file_uploader("Upload .zip experiment file", type="zip")
        
        if uploaded_file is not None:
            try:
                # Parse File
                config, agents_df, timeline_df = load_experiment_zip(uploaded_file)
                
                # Update Session State
                st.session_state['experiment_config'] = config
                st.session_state['experiment_data'] = {
                    "agents": agents_df,
                    "timeline": timeline_df
                }
                
                st.success(f"Loaded Experiment (Seed: {config['seed']})")
                st.markdown("**Next Step:** Go to the 'Run Experiment' tab to tweak these parameters, or 'Analysis Dashboard' to view the loaded data.")
                
            except Exception as e:
                st.error(f"Error loading file: {e}")
