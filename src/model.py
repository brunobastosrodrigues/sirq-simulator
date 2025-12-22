import mesa
import pandas as pd
import numpy as np
import os
import datetime
import json
from src.agents import TruckAgent
from src.config import *

class ChargingStationModel(mesa.Model):
    def __init__(self, num_chargers, strategy="FIFO", seed=None):
        # 1. FIXED SEEDING FOR COMPARABILITY
        super().__init__()
        self._seed = seed
        if seed is not None:
            self.random.seed(seed)
            np.random.seed(seed) # Force Numpy to sync with Mesa
            
        self.num_chargers = num_chargers
        self.strategy = strategy
        self.charging_spots = num_chargers
        self.schedule = mesa.time.RandomActivation(self)
        self.grid = mesa.space.MultiGrid(width=3, height=num_chargers + 10, torus=False)
        self.current_id = 0
        
        # Logs
        self.kpi_energy_sold = 0
        self.kpi_revenue = 0
        self.kpi_preemptions = 0
        self.kpi_failed_critical = 0
        self.agent_log = []
        self.system_log = []

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Queue_Length": lambda m: len([a for a in m.schedule.agents if a.status == "Queuing"]),
                "Preemptions": "kpi_preemptions"
            }
        )
        self.running = True

    def step(self):
        self._spawn_traffic()
        if self.strategy == "FIFO":
            self._logic_fifo()
        elif self.strategy == "SIRQ":
            self._logic_sirq()
        self.schedule.step()
        self._log_system_state()

    def _spawn_traffic(self):
        minute = self.schedule.steps % 1440
        hour = (minute // 60)
        
        prob = HOURLY_ARRIVAL_RATES["NIGHT"]
        if 6 <= hour < 10: prob = HOURLY_ARRIVAL_RATES["MORNING_PEAK"]
        elif 10 <= hour < 15: prob = HOURLY_ARRIVAL_RATES["MIDDAY"]
        elif 15 <= hour < 19: prob = HOURLY_ARRIVAL_RATES["EVENING_PEAK"]
        elif 19 <= hour < 24: prob = HOURLY_ARRIVAL_RATES["LATE"]

        # Use self.random (Mesa's RNG) to ensure seed consistency
        if self.random.random() < prob:
            # Urgency Distribution
            urgency = self.random.random() # Simplified Beta approx for speed
            self.current_id += 1
            agent = TruckAgent(self.current_id, self, urgency)
            self.schedule.add(agent)
            self.grid.place_agent(agent, (0, 0))

    # ... [Keep _logic_fifo, _logic_sirq, and log methods exactly as before] ...
    
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
            if (highest_bidder.bid > victim.bid * PREEMPTION_PREMIUM) and (victim.urgency < 0.8):
                self.log_departure(victim, "Preempted")
                self.kpi_preemptions += 1
                highest_bidder.status = "Charging"

    def _log_system_state(self):
        active_chargers = len([a for a in self.schedule.agents if a.status == "Charging"])
        queue_len = len([a for a in self.schedule.agents if a.status == "Queuing"])
        self.system_log.append({
            "Step": self.schedule.steps,
            "Active_Chargers": active_chargers,
            "Queue_Length": queue_len,
            "Total_Revenue": round(self.kpi_revenue, 2),
            "Strategy": self.strategy # Key for comparison plots
        })

    def log_departure(self, agent, reason):
        if reason in ["Left (Impatient)", "Preempted"] and agent.urgency > 0.7:
            self.kpi_failed_critical += 1
        self.agent_log.append({
            "ID": agent.unique_id,
            "Urgency": round(agent.urgency, 3),
            "Bid": agent.bid,
            "Outcome": reason,
            "Wait_Time": agent.wait_time,
            "Strategy": self.strategy # Key for comparison plots
        })
