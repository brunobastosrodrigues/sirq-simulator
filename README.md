# SIRQ: System for Interactive Reservation and Queue Management

A simulator for optimizing Electric Truck charging station turnover using auction-based prioritization.

<img width="368" height="348" alt="image" src="https://github.com/user-attachments/assets/9ad4bb85-7c9b-4642-9ca0-54b041d2f660" />


## Features
- **Benchmark Mode**: Real-time side-by-side comparison of FIFO vs SIRQ.
- **Metrics**: Tracks Revenue, Wait Time, and Critical Delivery Failures.
- **Reproducibility**: Export/Import experiments via ZIP for peer review.

## How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Run the workbench: `streamlit run app.py`
3. Select "Run Experiment" from the sidebar.

## Docker Support
`docker build -t sirq .`

`docker run -p 8501:8501 sirq`
