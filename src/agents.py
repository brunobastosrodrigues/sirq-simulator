import mesa
import numpy as np
from src.config import *

class TruckAgent(mesa.Agent):
    def __init__(self, unique_id, model, urgency):
        super().__init__(unique_id, model)
        # -- State --
        self.soc = np.random.randint(10, 30)
        self.initial_soc = self.soc # Track starting point
        self.target_soc = 85
        self.urgency = urgency
        
        # -- Economics --
        base_bid = np.random.uniform(10, 20)
        self.bid = round(base_bid * (1 + (self.urgency * 4)), 2)
        
        # -- Precise Timing Metrics --
        self.arrival_step = self.model.schedule.steps
        self.start_charge_step = None
        self.end_charge_step = None
        self.wait_time = 0
        
        # -- Performance Metrics --
        self.charged_kwh = 0
        self.status = "Queuing" 

    def step(self):
        if self.status == "Charging":
            self._charge()
        elif self.status == "Queuing":
            self._wait()

    def _wait(self):
        self.wait_time += 1
        patience_limit = MAX_WAIT_MINUTES * (1 + self.urgency) 
        if self.wait_time > patience_limit:
            self.model.log_departure(self, "Left (Impatient)")
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)

    def _charge(self):
        # Capture start time
        if self.start_charge_step is None:
            self.start_charge_step = self.model.schedule.steps

        # Physics & Inefficiency Logic
        kwh_added = CHARGER_POWER_KW / 60.0
        # Simulated CC-CV curve: Charging slows above 80%
        efficiency_factor = 1.0 if self.soc < 80 else 0.5
        
        real_kwh = kwh_added * efficiency_factor
        real_soc = (real_kwh / TRUCK_BATTERY_CAPACITY) * 100

        self.soc += real_soc
        self.charged_kwh += real_kwh
        self.model.kpi_energy_sold += real_kwh
        self.model.kpi_revenue += (real_kwh * PRICE_PER_KWH)

        if self.soc >= self.target_soc:
            self.model.log_departure(self, "Completed")
            self.model.charging_spots += 1
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)
