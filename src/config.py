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
    # 1.2 means you must pay 20% more than the incumbent to take their spot.
    "preemption_premium": 1.2,   
    
    # --- SMART PRICING (NEW EXTENSION) ---
    # Dynamic pricing based on station utilization (Queue + Active / Total Spots)
    "enable_smart_pricing": True, # Toggle dynamic congestion pricing
    "surge_sensitivity": 0.5,     # Aggressiveness: 0.5 means price rises 50% at 100% utilization
    "max_price_cap": 2.00,        # Regulatory Cap ($/kWh)
    
    # --- TRAFFIC MIX (Probabilities must sum to 1.0) ---
    "prob_critical": 0.20,       # 20% High Priority (Perishable/JIT)
    "prob_standard": 0.60,       # 60% Normal (FMCG/General Freight)
    "prob_economy": 0.20,        # 20% Low Priority (Bulk/Gig-Worker)
    
    # --- SIMULATION ---
    "traffic_multiplier": 1.0    # 1.0 = Normal, 1.5 = Heavy, etc.
}

# --- AGENT PROFILES (SCIENTIFIC & ECONOMIC) ---
TRUCK_PROFILES = {
    "CRITICAL": {
        # Profile: Just-In-Time (JIT) Logistics, Perishable Goods, Medical
        # Behavior: Cannot afford to wait. Will pay massive premiums.
        
        # Economic Parameters
        "vot_range": (150.0, 300.0), # $ Value of Time per Hour
        "price_sensitivity": 0.1,    # Inelastic
        "max_price_tolerance": 5.00, # $ Willingness to Pay per kWh (High tolerance)
        
        # Queue Behavior
        "patience": 240,             # Minutes
        "urgency_range": (0.8, 1.0), 
        
        # Visuals
        "color": "#ff4b4b",          # Red
        "border": "3px solid #b71c1c"
    },
    
    "STANDARD": {
        # Profile: Corporate Fleets, FMCG, Scheduled Delivery
        # Behavior: Rational economic actors.
        
        # Economic Parameters
        "vot_range": (50.0, 80.0),   # $ Value of Time per Hour
        "price_sensitivity": 0.5,    # Elastic
        "max_price_tolerance": 1.50, # $ Willingness to Pay per kWh
        
        # Queue Behavior
        "patience": 120,             # Minutes
        "urgency_range": (0.4, 0.7), 
        
        # Visuals
        "color": "#3498db",          # Blue
        "border": "1px solid #2980b9"
    },
    
    "ECONOMY": {
        # Profile: Owner-Operators, Bulk Haulage, Empty Returns
        # Behavior: Highly price sensitive. 
        
        # Economic Parameters
        "vot_range": (15.0, 30.0),   # $ Value of Time per Hour
        "price_sensitivity": 0.9,    # Highly Elastic
        "max_price_tolerance": 0.80, # $ Willingness to Pay per kWh (Low tolerance)
        
        # Queue Behavior
        "patience": 45,              # Minutes
        "urgency_range": (0.0, 0.3), 
        
        # Visuals
        "color": "#95a5a6",          # Gray
        "border": "1px dashed #7f8c8d"
    }
}