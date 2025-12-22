import mesa
import numpy as np
from src.config import TRUCK_PROFILES

class TruckAgent(mesa.Agent):
    def __init__(self, unique_id, model, profile_type, config):
        super().__init__(unique_id, model)
        self.profile_type = profile_type
        self.config = config
        
        # --- 1. Load Economic Profile ---
        profile_data = TRUCK_PROFILES[profile_type]
        self.color = profile_data["color"]
        self.border = profile_data["border"]
        
        # --- 2. Determine "Value of Time" (VOT) ---
        # How much money do I lose per hour of waiting?
        vot_min, vot_max = profile_data["vot_range"]
        self.value_of_time = np.random.uniform(vot_min, vot_max)
        
        # --- 3. Physics State ---
        self.soc = np.random.randint(10, 30)
        self.target_soc = 85
        self.wait_time = 0
        self.status = "Queuing"
        
        # --- 4. Rational Bidding Calculation ---
        self._calculate_initial_bid()

    def _calculate_initial_bid(self):
        """
        Determines the bid based on Economic Rationality.
        WTP = Base Fee + (Value of Time * Expected Wait)
        """
        base_fee = self.config.get("base_service_fee", 10.0)
        
        # Heuristic: Agents estimate queue wait. 
        # For simplicity, we assume they see the queue length and guess 15 mins per truck.
        queue_len = len([a for a in self.model.schedule.agents if a.status == "Queuing"])
        estimated_wait_hours = (queue_len * 15) / 60.0 
        
        # If queue is empty, expect 0 wait, but bid minimum to enter
        if estimated_wait_hours < 0.1: estimated_wait_hours = 0.1
        
        # THE CORE FORMULA
        # We add a little randomness (10%) to simulate imperfect human info
        rational_bid = base_fee + (self.value_of_time * estimated_wait_hours)
        noise = np.random.uniform(0.9, 1.1) 
        
        self.bid = round(rational_bid * noise, 2)

    def step(self):
        if self.status == "Charging":
            self._charge()
        elif self.status == "Queuing":
            self._wait()

    def _wait(self):
        self.wait_time += 1
        
        # --- Dynamic Bidding (Panic Logic) ---
        # If I am CRITICAL and I've waited too long, I panic and raise my bid.
        if self.profile_type == "CRITICAL" and self.wait_time % 30 == 0:
            self.bid += (self.value_of_time / 4) # Add 15 mins worth of value to the bid
        
        # --- Patience / Leaving Logic ---
        patience_limit = TRUCK_PROFILES[self.profile_type]["patience"]
        
        if self.wait_time > patience_limit:
            self.model.log_departure(self, "Left (Impatient)")
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)

    def _charge(self):
        # Physics logic remains standard
        power = self.config["charger_power"]
        capacity = self.config["battery_capacity"]
        
        kwh_added = power / 60.0
        efficiency = 1.0 if self.soc < 80 else 0.5
        real_kwh = kwh_added * efficiency
        real_soc = (real_kwh / capacity) * 100

        self.soc += real_soc
        self.model.kpi_revenue += (real_kwh * self.config["price_per_kwh"])

        if self.soc >= self.target_soc:
            self.model.log_departure(self, "Completed")
            self.model.charging_spots += 1
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)