# src/config.py

# --- DEFAULTS (Can be overridden by Dashboard) ---
DEFAULT_CONFIG = {
    # --- PHYSICS ---
    "charger_power": 150.0,      # kW (DC Fast Charging)
    "battery_capacity": 500.0,   # kWh (Heavy Duty Truck Battery)
    
    # --- ECONOMICS ---
    "price_per_kwh": 0.50,       # $ (Base Grid Price)
    "base_service_fee": 10.0,    # $ (Minimum entry fee to join queue)
    "auction_increment": 5.0,    # $ (Min step to outbid someone)
    
    # Preemption Logic (The "Kick-out" threshold)
    # A challenger must bid at least X times the current user's bid to preempt them.
    # 1.2 means you must pay 20% more than the incumbent to take their spot.
    "preemption_premium": 1.2,   
    
    # --- TRAFFIC MIX (Probabilities must sum to 1.0) ---
    "prob_critical": 0.20,       # 20% High Priority (Perishable/JIT)
    "prob_standard": 0.60,       # 60% Normal (FMCG/General Freight)
    "prob_economy": 0.20,        # 20% Low Priority (Bulk/Gig-Worker)
    
    # --- SIMULATION ---
    "traffic_multiplier": 1.0    # 1.0 = Normal, 1.5 = Heavy, etc.
}

# --- AGENT PROFILES (SCIENTIFIC & ECONOMIC) ---
# "Value of Time" (VOT) is the key metric for Transport Economics.
# It represents the monetary loss per hour of waiting.

TRUCK_PROFILES = {
    "CRITICAL": {
        # Profile: Just-In-Time (JIT) Logistics, Perishable Goods, Medical
        # Behavior: Cannot afford to wait. Will pay massive premiums.
        
        # Economic Parameters
        "vot_range": (150.0, 300.0), # $ Value of Time per Hour (High penalty for lateness)
        "price_sensitivity": 0.1,    # Inelastic: Will pay high prices (Low sensitivity)
        
        # Queue Behavior
        "patience": 240,             # Minutes: Will wait 4 hours before "Failure" (Desperate)
        "urgency_range": (0.8, 1.0), # Legacy Metric (0-1 score)
        
        # Visuals
        "color": "#ff4b4b",          # Red
        "border": "3px solid #b71c1c"
    },
    
    "STANDARD": {
        # Profile: Corporate Fleets, FMCG, Scheduled Delivery
        # Behavior: Rational economic actors. Trade off time vs money efficiently.
        
        # Economic Parameters
        "vot_range": (50.0, 80.0),   # $ Value of Time per Hour (Driver wages + Fuel)
        "price_sensitivity": 0.5,    # Elastic: Balances cost vs speed
        
        # Queue Behavior
        "patience": 120,             # Minutes: Will wait 2 hours max
        "urgency_range": (0.4, 0.7), # Legacy Metric
        
        # Visuals
        "color": "#3498db",          # Blue
        "border": "1px solid #2980b9"
    },
    
    "ECONOMY": {
        # Profile: Owner-Operators, Bulk Haulage (Sand/Gravel), Empty Returns
        # Behavior: Highly price sensitive. Profit margins are thin. 
        # Fairness Note: These agents suffer "Starvation" in SIRQ systems.
        
        # Economic Parameters
        "vot_range": (15.0, 30.0),   # $ Value of Time per Hour (Low margin)
        "price_sensitivity": 0.9,    # Highly Elastic: Will leave if price surges
        
        # Queue Behavior
        "patience": 45,              # Minutes: Leaves quickly to find cheaper station
        "urgency_range": (0.0, 0.3), # Legacy Metric
        
        # Visuals
        "color": "#95a5a6",          # Gray
        "border": "1px dashed #7f8c8d"
    }
}