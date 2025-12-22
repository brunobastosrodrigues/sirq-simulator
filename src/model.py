import mesa
import pandas as pd
import numpy as np
import os
import datetime
import json
from src.agents import TruckAgent
from src.config import DEFAULT_CONFIG

class ChargingStationModel(mesa.Model):
    def __init__(self, num_chargers, strategy="FIFO", seed=None, user_config=None):
        super().__init__()
        self._seed = seed
        if seed is not None:
            self.random.seed(seed)
            np.random.seed(seed)
            
        # MERGE Config: Defaults + User Overrides
        self.config = DEFAULT_CONFIG.copy()
        if user_config:
            self.config.update(user_config)
            
        self.num_chargers = num_chargers
        self.strategy = strategy
        self.charging_spots = num_chargers
        self.schedule = mesa.time.RandomActivation(self)
        self.grid = mesa.space.MultiGrid(width=3, height=num_chargers + 10, torus=False)
        self.current_id = 0
        
        # Metrics
        self.kpi_energy_sold = 0
        self.kpi_revenue = 0
        self.kpi_preemptions = 0
        self.kpi_failed_critical = 0
        self.agent_log = []
        self.system_log = []

        self.running = True

    def step(self):
        self._spawn_traffic()
        if self.strategy == "FIFO": self._logic_fifo()
        elif self.strategy == "SIRQ": self._logic_sirq()
        self.schedule.step()
        self._log_system_state()

    def _spawn_traffic(self):
        # Time-of-day logic
        minute = self.schedule.steps % 1440
        hour = minute // 60
        
        # Probabilities
        if 6 <= hour < 10 or 15 <= hour < 19: prob = 0.35 # Peak
        elif 0 <= hour < 6: prob = 0.05
        else: prob = 0.15
        
        if self.random.random() < prob:
            self.current_id += 1
            
            # --- PROFILE SELECTION ---
            p_crit = self.config["prob_critical"]
            p_std = self.config["prob_standard"]
            p_eco = self.config["prob_economy"]
            
            # Normalize
            total = p_crit + p_std + p_eco
            choices = ["CRITICAL", "STANDARD", "ECONOMY"]
            weights = [p_crit/total, p_std/total, p_eco/total]
            
            profile = np.random.choice(choices, p=weights)
            
            agent = TruckAgent(self.current_id, self, profile, self.config)
            self.schedule.add(agent)
            self.grid.place_agent(agent, (0, 0))

    def _logic_fifo(self):
        queue = sorted([a for a in self.schedule.agents if a.status == "Queuing"], key=lambda x: x.unique_id)
        while self.charging_spots > 0 and queue:
            truck = queue.pop(0)
            truck.status = "Charging"
            self.charging_spots -= 1

    def _logic_sirq(self):
        queue = sorted([a for a in self.schedule.agents if a.status == "Queuing"], key=lambda x: x.bid, reverse=True)
        chargers = [a for a in self.schedule.agents if a.status == "Charging"]
        
        while self.charging_spots > 0 and queue:
            truck = queue.pop(0)
            truck.status = "Charging"
            self.charging_spots -= 1

        if queue and chargers:
            highest_bidder = queue[0]
            chargers.sort(key=lambda x: x.bid)
            victim = chargers[0]
            
            # Use Configured Preemption Premium
            premium = self.config["preemption_premium"]
            
            # Logic: Bidder > Victim * Premium AND Victim is not Critical
            if (highest_bidder.bid > victim.bid * premium) and (victim.profile_type != "CRITICAL"):
                self.log_departure(victim, "Preempted")
                self.kpi_preemptions += 1
                highest_bidder.status = "Charging"

    def log_departure(self, agent, reason):
        if reason in ["Left (Impatient)", "Preempted"] and agent.profile_type == "CRITICAL":
            self.kpi_failed_critical += 1
        
        self.agent_log.append({
            "ID": agent.unique_id,
            "Profile": agent.profile_type,
            "Urgency": round(agent.urgency, 3),
            "Bid": agent.bid,
            "Outcome": reason,
            "Wait_Time": agent.wait_time,
            "Strategy": self.strategy  # <--- THIS WAS MISSING
        })

    def _log_system_state(self):
        self.system_log.append({
            "Step": self.schedule.steps,
            "Total_Revenue": round(self.kpi_revenue, 2),
            "Queue_Length": len([a for a in self.schedule.agents if a.status == "Queuing"]),
            "Strategy": self.strategy
        })