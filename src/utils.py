import pandas as pd
import json
import io
import zipfile

def create_experiment_zip(config, agent_df, system_df):
    """
    Bundles configuration and results into a single verifiable ZIP file.
    """
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Save Configuration
        zf.writestr("config.json", json.dumps(config, indent=4))
        
        # 2. Save DataFrames
        zf.writestr("agents.csv", agent_df.to_csv(index=False))
        zf.writestr("timeline.csv", system_df.to_csv(index=False))
        
    buffer.seek(0)
    return buffer

def load_experiment_zip(uploaded_file):
    """
    Extracts config and results from an uploaded ZIP.
    """
    with zipfile.ZipFile(uploaded_file, "r") as zf:
        # 1. Load Config
        config = json.loads(zf.read("config.json").decode("utf-8"))
        
        # 2. Load DataFrames
        agents_df = pd.read_csv(io.BytesIO(zf.read("agents.csv")))
        timeline_df = pd.read_csv(io.BytesIO(zf.read("timeline.csv")))
        
    return config, agents_df, timeline_df