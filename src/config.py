# src/config.py

# --- DEFAULTS (Can be overridden by Dashboard) ---
DEFAULT_CONFIG = {
    # Physics
    "charger_power": 150.0,      # kW
    "battery_capacity": 500.0,   # kWh
    
    # Economics
    "price_per_kwh": 0.50,       # $
    "preemption_premium": 1.5,   # Multiplier to kick someone out
    
    # Traffic Mix (Probabilities must sum to 1.0)
    "prob_critical": 0.20,       # 20% High Priority
    "prob_standard": 0.60,       # 60% Normal
    "prob_economy": 0.20,        # 20% Low Priority
}

# --- AGENT PROFILES (The Logic) ---
TRUCK_PROFILES = {
    "CRITICAL": {
        "urgency_range": (0.8, 1.0),
        "bid_multiplier": 5.0,     # Pays 5x base price
        "patience_factor": 1.5,    # Waits longer because it NEEDS charge
        "color": "#ff4b4b",        # Red
        "border": "3px solid #b71c1c"
    },
    "STANDARD": {
        "urgency_range": (0.4, 0.7),
        "bid_multiplier": 2.5,
        "patience_factor": 1.0,
        "color": "#3498db",        # Blue
        "border": "1px solid #2980b9"
    },
    "ECONOMY": {
        "urgency_range": (0.0, 0.3),
        "bid_multiplier": 1.2,
        "patience_factor": 0.5,    # Leaves quickly if queue is long
        "color": "#95a5a6",        # Gray
        "border": "1px dashed #7f8c8d"
    }
}