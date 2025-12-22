# SIRQ: System for Interactive Reservation and Queueing
### A Market-Based Mechanism for Electric Logistics Infrastructure

**SIRQ** is a simulation platform designed to evaluate the economic and operational impact of replacing First-In-First-Served (FIFO) queues with **Real-Time Auctions** for electric truck charging.

<img width="600" alt="SIRQ Dashboard" src="https://github.com/user-attachments/assets/9ad4bb85-7c9b-4642-9ca0-54b041d2f660" />

---

## 🧪 Key goals
* **RQ1: Economic Efficiency:** Does an auction mechanism maximize infrastructure revenue compared to FIFO?
* **RQ2: Supply Chain Resilience:** Can dynamic prioritization prevent "System Collapse" for critical Just-In-Time (JIT) logistics?
* **RQ3: Micro-Economic Rationality:** How do heterogeneous agents (High vs. Low Value-of-Time) behave under pricing pressure?
* **RQ4: Social Equity:** Quantifying the "starvation" of low-income drivers and modeling subsidy-based redistribution policies.

---

## 🚀 Key Features

### 1. Micro-Economic Agents
Agents are no longer simple rule-based entities. They act as **Rational Economic Actors** defined by:
* **Value of Time (VOT):** Monetary loss per hour of waiting (e.g., Critical = \$150/hr vs. Economy = \$20/hr).
* **Price Sensitivity:** Elasticity of demand based on profile type.
* **Dynamic Bidding:** Bids are calculated in real-time based on `Base Fee + (VOT * Expected Wait)`.

### 2. Monte Carlo Simulations
* **Batch Processing:** Run N=30 to N=200 simulations in parallel to generate statistically significant datasets (N > 30 for Central Limit Theorem).
* **Parameter Sweeps:** Automatically test across multiple Traffic Loads (0.8x to 2.0x capacity).
* **Confidence Intervals:** Automatic calculation of 95% CI for all revenue and wait-time metrics.

### 3. Analytics
A dedicated module (`src/analytics.py`) generating 24+ scientific plots, including:
* **Violin Plots & ECDFs** for Wait Time distributions.
* **Gini Coefficients** to measure inequality.
* **Scatter Plots (OLS Regression)** to verify Bidding Rationality.
* **Welfare Analysis** calculating total societal economic loss.

### 4. Reproducibility
* **Data Manager:** Export the full experiment (Summary Statistics + Agent-Level Micro-Logs) as a verifiable `.zip` file.
* **Import:** Reviewers can load the ZIP file to reproduce the exact graphs without re-running the simulation.

---

## 🛠️ Installation & Usage

### Method 1: Local Python (Recommended)
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/brunobastosrodrigues/sirq-simulator.git](https://github.com/brunobastosrodrigues/sirq-simulator.git)
    cd sirq-simulator
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the simulator:**
    ```bash
    streamlit run app.py
    ```

### Method 2: Docker
Run the simulator in an isolated container.
```bash
docker build -t sirq .
docker run -p 8501:8501 sirq
