# src/config.py

# --- Physics Constants ---
CHARGER_POWER_KW = 150.0       # DC Fast Charger
TRUCK_BATTERY_CAPACITY = 500.0 # kWh (e.g., Tesla Semi / Volvo VNR)
SIMULATION_MINUTES = 1440      # 24 Hours

# --- Business Logic ---
PRICE_PER_KWH = 0.50           # Base price in $
PREEMPTION_PREMIUM = 1.5       # Bidder must pay 1.5x the current user's value to kick them
MAX_WAIT_MINUTES = 90          # Max patience before leaving

# --- Traffic Patterns ---
# Probability of arrival per minute based on hour of day
HOURLY_ARRIVAL_RATES = {
    "NIGHT": 0.05,  # 00:00 - 06:00
    "MORNING_PEAK": 0.35, # 06:00 - 10:00
    "MIDDAY": 0.15, # 10:00 - 15:00
    "EVENING_PEAK": 0.40, # 15:00 - 19:00
    "LATE": 0.10    # 19:00 - 24:00
}
