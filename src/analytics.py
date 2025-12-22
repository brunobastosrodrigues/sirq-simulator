import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import statsmodels.api as sm

class ScientificPlotter:
    def __init__(self, df, df_micro=None):
        self.df = df
        self.df_micro = df_micro
        self.colors = {"FIFO": "#3498db", "SIRQ": "#2ecc71"}
        self.profile_colors = {"CRITICAL": "#ff4b4b", "STANDARD": "#3498db", "ECONOMY": "#95a5a6"}

    # =========================================================================
    # RQ1: ECONOMIC EFFICIENCY
    # =========================================================================
    def rq1_revenue_ci(self):
        summary = self.df.groupby(["Traffic_Load", "Strategy"])["Revenue"].agg(["mean", "std", "count"]).reset_index()
        summary['ci'] = 1.96 * (summary['std'] / np.sqrt(summary['count']))
        fig = go.Figure()
        for s in self.df["Strategy"].unique():
            sub = summary[summary["Strategy"] == s]
            fig.add_trace(go.Scatter(x=sub["Traffic_Load"], y=sub["mean"], error_y=dict(type='data', array=sub['ci'], visible=True), mode='lines+markers', name=s, line=dict(color=self.colors.get(s, "gray"))))
        fig.update_layout(title="<b>Mean Revenue vs Load</b> (95% CI)", xaxis_title="Traffic Load", yaxis_title="Revenue ($)", template="plotly_white")
        return fig

    def rq1_revenue_dist(self):
        fig = px.violin(self.df, x="Traffic_Load", y="Revenue", color="Strategy", box=True, title="<b>Revenue Density Distribution</b>", color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig

    def rq1_revenue_delta(self):
        pivoted = self.df.pivot_table(index=["Traffic_Load"], columns="Strategy", values="Revenue", aggfunc="mean")
        if "FIFO" in pivoted.columns and "SIRQ" in pivoted.columns:
            pivoted["Delta_Pct"] = ((pivoted["SIRQ"] - pivoted["FIFO"]) / pivoted["FIFO"]) * 100
            pivoted = pivoted.reset_index()
            fig = px.bar(pivoted, x="Traffic_Load", y="Delta_Pct", text_auto='.1f', title="<b>Relative Revenue Gain (SIRQ vs FIFO)</b>", color="Delta_Pct", color_continuous_scale="Greens")
            fig.update_layout(yaxis_title="% Improvement", template="plotly_white")
            return fig
        return None

    def rq1_utilization_proxy(self):
        self.df["Rev_Per_Unit"] = self.df["Revenue"] / self.df["Traffic_Load"]
        fig = px.box(self.df, x="Traffic_Load", y="Rev_Per_Unit", color="Strategy", title="<b>Revenue Efficiency per Unit of Traffic</b>", color_discrete_map=self.colors)
        return fig

    def rq1_opportunity_cost(self):
        # Includes Balked Agents (Lost Demand)
        if "Balked_Agents" not in self.df.columns:
            self.df["Balked_Agents"] = 0
        self.df["Lost_Rev"] = (self.df["Critical_Failures"] + self.df["Balked_Agents"]) * 50 
        fig = px.bar(self.df.groupby(["Traffic_Load", "Strategy"])["Lost_Rev"].mean().reset_index(), x="Traffic_Load", y="Lost_Rev", color="Strategy", barmode="group", title="<b>Est. Lost Opportunity (Failures + Balking)</b>", color_discrete_map=self.colors)
        return fig

    def rq1_revenue_stability(self):
        cv = self.df.groupby(["Traffic_Load", "Strategy"])["Revenue"].agg(lambda x: x.std() / x.mean() * 100).reset_index().rename(columns={"Revenue": "CV"})
        fig = px.line(cv, x="Traffic_Load", y="CV", color="Strategy", markers=True, title="<b>Revenue Volatility (CV)</b>", color_discrete_map=self.colors)
        return fig

    def rq1_pricing_dynamics(self):
        # Estimates Demand Response by plotting Balked Agents (High Price -> High Balking)
        if "Balked_Agents" in self.df.columns:
            fig = px.box(self.df, x="Traffic_Load", y="Balked_Agents", color="Strategy", title="<b>Demand Response: Agents refusing High Prices</b>", color_discrete_map=self.colors)
            return fig
        return None

    # =========================================================================
    # RQ2: SERVICE RELIABILITY
    # =========================================================================
    def rq2_critical_wait_box(self):
        fig = px.box(self.df, x="Traffic_Load", y="Avg_Wait_Critical", color="Strategy", title="<b>Critical Wait Times (Distribution)</b>", color_discrete_map=self.colors)
        fig.update_layout(yaxis_title="Minutes", template="plotly_white")
        return fig

    def rq2_failure_rate(self):
        fig = px.line(self.df.groupby(["Traffic_Load", "Strategy"])["Critical_Failures"].mean().reset_index(), x="Traffic_Load", y="Critical_Failures", color="Strategy", markers=True, title="<b>System Collapse Rate (Critical Failures)</b>", color_discrete_map=self.colors)
        return fig

    def rq2_ecdf_wait(self):
        max_load = self.df["Traffic_Load"].max()
        subset = self.df[self.df["Traffic_Load"] == max_load]
        fig = px.ecdf(subset, x="Avg_Wait_Critical", color="Strategy", title=f"<b>ECDF: Probability of Wait Time < X</b> (Load {max_load}x)", color_discrete_map=self.colors)
        return fig
    
    def rq2_max_wait_analysis(self):
        if self.df_micro is not None:
            crit = self.df_micro[self.df_micro["Profile"] == "CRITICAL"]
            max_waits = crit.groupby(["Traffic_Load", "Strategy"])["Wait_Time"].max().reset_index()
            fig = px.bar(max_waits, x="Traffic_Load", y="Wait_Time", color="Strategy", barmode="group", title="<b>Worst-Case Scenario (Max Wait)</b>", color_discrete_map=self.colors)
            return fig
        return None

    def rq2_on_time_performance(self):
        if self.df_micro is not None:
            # FIX: Use .copy() to avoid SettingWithCopyWarning
            crit = self.df_micro[self.df_micro["Profile"] == "CRITICAL"].copy()
            crit["On_Time"] = crit["Wait_Time"] <= 15
            otp = crit.groupby(["Traffic_Load", "Strategy"])["On_Time"].mean().reset_index()
            fig = px.line(otp, x="Traffic_Load", y="On_Time", color="Strategy", markers=True, title="<b>On-Time Performance (% Served < 15m)</b>", color_discrete_map=self.colors)
            fig.update_layout(yaxis_tickformat=".0%")
            return fig
        return None

    def rq2_preemption_turbulence(self):
        if "Preemptions" in self.df.columns:
            fig = px.bar(self.df.groupby(["Traffic_Load", "Strategy"])["Preemptions"].mean().reset_index(), x="Traffic_Load", y="Preemptions", color="Strategy", title="<b>Queue Turbulence (Preemptions)</b>", color_discrete_map=self.colors)
            return fig
        return None

    # =========================================================================
    # RQ3: MICRO-ECONOMICS
    # =========================================================================
    def rq3_bidding_rationality(self):
        if self.df_micro is None: return None
        subset = self.df_micro.sample(n=min(len(self.df_micro), 2000), random_state=42)
        fig = px.scatter(subset, x="Value_of_Time", y="Bid", color="Profile", facet_col="Strategy",
                         title="<b>Rationality Check: Correlation of VOT vs Bid</b>",
                         trendline="ols", opacity=0.5, color_discrete_map=self.profile_colors)
        return fig

    def rq3_welfare_loss(self):
        self.df["Estimated_Pain"] = ((self.df["Avg_Wait_Critical"]/60 * 225) + (self.df["Avg_Wait_Economy"]/60 * 22))
        fig = px.bar(self.df.groupby(["Traffic_Load", "Strategy"])["Estimated_Pain"].mean().reset_index(),
                     x="Traffic_Load", y="Estimated_Pain", color="Strategy", barmode="group",
                     title="<b>Total Societal Welfare Loss (Wait Cost $)</b>", color_discrete_map=self.colors)
        return fig

    def rq3_bid_landscape(self):
        if self.df_micro is None: return None
        sirq_data = self.df_micro[self.df_micro["Strategy"] == "SIRQ"]
        fig = px.histogram(sirq_data, x="Bid", color="Profile", barmode="overlay", title="<b>Bid Landscape (SIRQ Only)</b>", color_discrete_map=self.profile_colors)
        return fig

    def rq3_winning_bid_trend(self):
        if self.df_micro is None: return None
        winners = self.df_micro[(self.df_micro["Strategy"] == "SIRQ") & (self.df_micro["Outcome"].isin(["Completed", "Preempted"]))]
        trend = winners.groupby("Traffic_Load")["Bid"].mean().reset_index()
        fig = px.line(trend, x="Traffic_Load", y="Bid", markers=True, title="<b>Market Clearing Price (Avg Winning Bid)</b>", color_discrete_sequence=["#2ecc71"])
        return fig

    def rq3_profile_win_rate(self):
        if self.df_micro is None: return None
        counts = self.df_micro[self.df_micro["Strategy"]=="SIRQ"].groupby(["Profile", "Outcome"]).size().unstack(fill_value=0)
        if "Completed" in counts.columns:
            counts["Win_Rate"] = counts["Completed"] / counts.sum(axis=1)
            fig = px.bar(counts.reset_index(), x="Profile", y="Win_Rate", title="<b>Profile Win Rate (SIRQ)</b>", color="Profile", color_discrete_map=self.profile_colors)
            return fig
        return None

    # =========================================================================
    # RQ4: SOCIAL IMPACT & EQUITY
    # =========================================================================
    def rq4_equity_gap(self):
        self.df["Equity_Gap"] = self.df["Avg_Wait_Economy"] - self.df["Avg_Wait_Critical"]
        summary = self.df.groupby(["Traffic_Load", "Strategy"])["Equity_Gap"].mean().reset_index()
        fig = px.line(summary, x="Traffic_Load", y="Equity_Gap", color="Strategy", markers=True, title="<b>Equity Gap (Economy Wait - Critical Wait)</b>", color_discrete_map=self.colors)
        return fig
    
    def rq4_starvation_scatter(self):
        # RESTORED: The original scatter plot requested
        fig = px.scatter(self.df, x="Avg_Wait_Critical", y="Avg_Wait_Economy", color="Strategy", facet_col="Traffic_Load", title="<b>Starvation: Economy vs Critical</b>", opacity=0.6, color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig

    def rq4_subsidy_potential(self):
        pivot = self.df.pivot_table(index="Traffic_Load", columns="Strategy", values="Revenue", aggfunc="mean")
        if "FIFO" in pivot.columns and "SIRQ" in pivot.columns:
            pivot["Subsidy_Pool"] = pivot["SIRQ"] - pivot["FIFO"]
            pivot = pivot.reset_index()
            fig = px.area(pivot, x="Traffic_Load", y="Subsidy_Pool", title="<b>Potential Subsidy Pool (Extra Revenue)</b>", color_discrete_sequence=["#27ae60"])
            return fig
        return None

    def rq4_gini_coefficient(self):
        if self.df_micro is None: return None
        
        def gini(x):
            total = 0
            for i, xi in enumerate(x[:-1], 1):
                total += np.sum(np.abs(xi - x[i:]))
            return total / (len(x)**2 * np.mean(x)) if len(x) > 0 and np.mean(x) > 0 else 0

        ginis = []
        for (load, strat), group in self.df_micro.groupby(["Traffic_Load", "Strategy"]):
            g = gini(group["Wait_Time"].values)
            ginis.append({"Traffic_Load": load, "Strategy": strat, "Gini": g})
            
        fig = px.line(pd.DataFrame(ginis), x="Traffic_Load", y="Gini", color="Strategy", markers=True, title="<b>Gini Coefficient (Inequality)</b>", color_discrete_map=self.colors)
        return fig

    def rq4_starvation_depth(self):
        if self.df_micro is None: return None
        eco = self.df_micro[self.df_micro["Profile"] == "ECONOMY"]
        depth = eco.groupby(["Traffic_Load", "Strategy"])["Wait_Time"].max().reset_index()
        fig = px.bar(depth, x="Traffic_Load", y="Wait_Time", color="Strategy", barmode="group", title="<b>Starvation Depth (Max Economy Wait)</b>", color_discrete_map=self.colors)
        return fig
    
    def rq4_access_rate(self):
        if self.df_micro is None: return None
        served = self.df_micro[self.df_micro["Outcome"] == "Completed"]
        fig = px.histogram(served, x="Profile", color="Strategy", barmode="group", title="<b>Service Access Count by Profile</b>", color_discrete_map=self.colors)
        return fig