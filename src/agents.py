import mesa
import numpy as np
from src.config import TRUCK_PROFILES

class TruckAgent(mesa.Agent):
    def __init__(self, unique_id, model, profile_type, config):
        super().__init__(unique_id, model)
        self.profile_type = profile_type
        self.config = config
        
        # Load Profile Data
        profile_data = TRUCK_PROFILES[profile_type]
        
        # -- Physics --
        self.soc = np.random.randint(10, 30)
        self.initial_soc = self.soc
        self.target_soc = 85
        
        # -- Urgency & Bidding --
        u_min, u_max = profile_data["urgency_range"]
        self.urgency = np.random.uniform(u_min, u_max)
        
        # Bid Calculation: Base Price + (Urgency * Multiplier * Randomness)
        base_bid = 15.0 # Base entry fee
        self.bid = round(base_bid * (1 + (self.urgency * profile_data["bid_multiplier"])), 2)
        
        # -- Visuals --
        self.color = profile_data["color"]
        self.border = profile_data["border"]
        
        # -- Metrics --
        self.arrival_step = self.model.schedule.steps
        self.wait_time = 0
        self.charged_kwh = 0
        self.status = "Queuing" 

    def step(self):
        if self.status == "Charging":
            self._charge()
        elif self.status == "Queuing":
            self._wait()

    def _wait(self):
        self.wait_time += 1
        # Patience based on Profile
        p_factor = TRUCK_PROFILES[self.profile_type]["patience_factor"]
        max_wait = 90 * p_factor
        
        if self.wait_time > max_wait:
            self.model.log_departure(self, "Left (Impatient)")
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)

    def _charge(self):
        # Use Dynamic Config for Power
        power = self.config["charger_power"]
        capacity = self.config["battery_capacity"]
        
        kwh_added = power / 60.0
        # Efficiency Curve (slower > 80%)
        efficiency = 1.0 if self.soc < 80 else 0.5
        
        real_kwh = kwh_added * efficiency
        real_soc = (real_kwh / capacity) * 100

        self.soc += real_soc
        self.charged_kwh += real_kwh
        self.model.kpi_energy_sold += real_kwh
        self.model.kpi_revenue += (real_kwh * self.config["price_per_kwh"])

        if self.soc >= self.target_soc:
            self.model.log_departure(self, "Completed")
            self.model.charging_spots += 1
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)