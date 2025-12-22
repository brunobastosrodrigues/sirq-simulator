import mesa
import pandas as pd
import numpy as np
import os
import datetime
import json
from src.agents import TruckAgent
from src.config import DEFAULT_CONFIG, TRUCK_PROFILES

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
        self.kpi_balked_agents = 0  # NEW: Count of lost customers
        
        # State
        self.current_price = self.config["price_per_kwh"]
        
        self.agent_log = []
        self.system_log = []

        self.running = True

    def step(self):
        # 1. Update Market Conditions (Smart Pricing)
        self._update_smart_pricing()
        
        # 2. Spawn New Traffic
        self._spawn_traffic()
        
        # 3. Execute Queue Logic
        if self.strategy == "FIFO": 
            self._logic_fifo()
        elif self.strategy == "SIRQ": 
            self._logic_sirq()
            
        # 4. Advance Agents
        self.schedule.step()
        self._log_system_state()

    def _update_smart_pricing(self):
        """
        Updates the electricity price based on real-time congestion (Surge Pricing).
        Formula: Price = Base * (1 + Sensitivity * Utilization)
        """
        if not self.config.get("enable_smart_pricing", False):
            self.current_price = self.config["price_per_kwh"]
            return

        # Calculate Utilization (Active + Queue / Capacity)
        active = len([a for a in self.schedule.agents if a.status == "Charging"])
        queued = len([a for a in self.schedule.agents if a.status == "Queuing"])
        total_load = active + queued
        
        capacity = max(self.num_chargers, 1)
        utilization_ratio = total_load / capacity
        
        # Surge Logic
        surge_factor = self.config["surge_sensitivity"]
        base_price = self.config["price_per_kwh"]
        
        # Calculate new price with Regulatory Cap
        new_price = base_price * (1 + (surge_factor * utilization_ratio))
        self.current_price = min(new_price, self.config["max_price_cap"])

    def _spawn_traffic(self):
        # Time-of-day logic
        minute = self.schedule.steps % 1440
        hour = minute // 60
        
        # Base Probabilities
        if 6 <= hour < 10 or 15 <= hour < 19: prob = 0.35 # Peak
        elif 0 <= hour < 6: prob = 0.05
        else: prob = 0.15
        
        # Apply Traffic Multiplier
        multiplier = self.config.get("traffic_multiplier", 1.0)
        prob = prob * multiplier
        
        if self.random.random() < prob:
            # --- PROFILE SELECTION ---
            p_crit = self.config["prob_critical"]
            p_std = self.config["prob_standard"]
            p_eco = self.config["prob_economy"]
            
            # Normalize
            total = p_crit + p_std + p_eco
            choices = ["CRITICAL", "STANDARD", "ECONOMY"]
            weights = [p_crit/total, p_std/total, p_eco/total]
            
            profile = np.random.choice(choices, p=weights)
            
            # --- SMART PRICING: BALKING CHECK ---
            # If the current price is too high, the agent leaves immediately.
            if self.config.get("enable_smart_pricing", False):
                tolerance = TRUCK_PROFILES[profile]["max_price_tolerance"]
                if self.current_price > tolerance:
                    self.kpi_balked_agents += 1
                    return # Agent does not enter system
            
            self.current_id += 1
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
            "Urgency": round(agent.urgency, 3) if hasattr(agent, 'urgency') else 0,
            "Value_of_Time": round(agent.value_of_time, 2),
            "Bid": round(agent.bid, 2),
            "Outcome": reason,
            "Wait_Time": agent.wait_time,
            "Strategy": self.strategy
        })

    def _log_system_state(self):
        self.system_log.append({
            "Step": self.schedule.steps,
            "Total_Revenue": round(self.kpi_revenue, 2),
            "Queue_Length": len([a for a in self.schedule.agents if a.status == "Queuing"]),
            "Strategy": self.strategy,
            "Current_Price": round(self.current_price, 2), # Log Dynamic Price
            "Balked_Agents": self.kpi_balked_agents
        })