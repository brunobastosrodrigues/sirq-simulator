import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

class ScientificPlotter:
    def __init__(self, df):
        self.df = df
        self.colors = {"FIFO": "#3498db", "SIRQ": "#2ecc71"}

    # --- RQ1: MACRO-ECONOMICS (Revenue) ---
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
        fig = px.violin(self.df, x="Traffic_Load", y="Revenue", color="Strategy", box=True, title="<b>Revenue Density</b>", color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig

    def rq1_revenue_delta(self):
        pivoted = self.df.pivot_table(index=["Traffic_Load"], columns="Strategy", values="Revenue", aggfunc="mean")
        if "FIFO" in pivoted.columns and "SIRQ" in pivoted.columns:
            pivoted["Delta_Pct"] = ((pivoted["SIRQ"] - pivoted["FIFO"]) / pivoted["FIFO"]) * 100
            pivoted = pivoted.reset_index()
            fig = px.bar(pivoted, x="Traffic_Load", y="Delta_Pct", text_auto='.1f', title="<b>SIRQ Revenue Gain (%)</b>", color="Delta_Pct", color_continuous_scale="Greens")
            fig.update_layout(yaxis_title="% Improvement", template="plotly_white")
            return fig
        return None

    # --- RQ2: SERVICE RELIABILITY ---
    def rq2_critical_wait_box(self):
        fig = px.box(self.df, x="Traffic_Load", y="Avg_Wait_Critical", color="Strategy", title="<b>Critical Wait Times</b>", color_discrete_map=self.colors)
        fig.update_layout(yaxis_title="Minutes", template="plotly_white")
        return fig

    def rq2_failure_rate(self):
        fig = px.line(self.df.groupby(["Traffic_Load", "Strategy"])["Critical_Failures"].mean().reset_index(), x="Traffic_Load", y="Critical_Failures", color="Strategy", markers=True, title="<b>Critical Failure Rate</b> (System Collapse)", color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig

    def rq2_ecdf_wait(self):
        max_load = self.df["Traffic_Load"].max()
        subset = self.df[self.df["Traffic_Load"] == max_load]
        fig = px.ecdf(subset, x="Avg_Wait_Critical", color="Strategy", title=f"<b>ECDF of Wait Times</b> (Load {max_load}x)", color_discrete_map=self.colors)
        fig.update_layout(yaxis_title="Probability", template="plotly_white")
        return fig

    # --- RQ3: MICRO-ECONOMICS (Rationality & Welfare) ---
    def rq3_bidding_rationality(self):
        """
        Scatter plot of Value of Time vs. Bid Amount.
        Hypothesis: In SIRQ, Bid should correlate with VOT (Rationality).
        """
        # Sample down if dataset is huge for performance
        subset = self.df.sample(n=min(len(self.df), 2000), random_state=42)
        fig = px.scatter(subset, x="Value_of_Time", y="Bid", color="Profile", facet_col="Strategy",
                         title="<b>Rationality Check:</b> Does Value-of-Time drive Bidding?",
                         trendline="ols", opacity=0.5)
        fig.update_layout(template="plotly_white")
        return fig

    def rq3_welfare_loss(self):
        """
        Calculates Total Economic Loss = (Wait Time / 60) * Value of Time
        This measures the 'pain' felt by the agents in dollars.
        """
        # Ensure we calculate metrics if they don't exist in the summary
        if "Wait_Time" in self.df.columns and "Value_of_Time" in self.df.columns:
            # Calculate individual loss per agent interaction (approximated from averages if using summary df)
            # Note: For accurate calculation, this usually needs agent-level data. 
            # Assuming 'df' here is the Monte Carlo summary which might aggregate. 
            # If df is Agent Log, this works perfectly. If df is Run Summary, we need a different approach.
            pass 
        
        # NOTE: For the dashboard, we are passing the Monte Carlo Summary (per run).
        # We need the 'Avg_Wait_Critical' * 'VOT_Critical' roughly.
        # Let's approximate Total System Pain (Cost of Waiting)
        
        # We will assume average VOT for Critical=$225, Standard=$65, Economy=$22
        self.df["Estimated_Pain"] = (
            (self.df["Avg_Wait_Critical"] / 60 * 225) + 
            (self.df["Avg_Wait_Economy"] / 60 * 22)
        )
        
        fig = px.bar(self.df.groupby(["Traffic_Load", "Strategy"])["Estimated_Pain"].mean().reset_index(),
                     x="Traffic_Load", y="Estimated_Pain", color="Strategy", barmode="group",
                     title="<b>Societal Welfare Loss</b> (Cost of Waiting in $)",
                     color_discrete_map=self.colors)
        fig.update_layout(yaxis_title="Est. Economic Loss ($)", template="plotly_white")
        return fig

    # --- RQ4: EQUITY & SOCIETY ---
    def rq4_equity_gap(self):
        self.df["Equity_Gap"] = self.df["Avg_Wait_Economy"] - self.df["Avg_Wait_Critical"]
        summary = self.df.groupby(["Traffic_Load", "Strategy"])["Equity_Gap"].mean().reset_index()
        fig = px.line(summary, x="Traffic_Load", y="Equity_Gap", color="Strategy", markers=True, title="<b>The Cost of Inequality</b> (Wait Time Gap)", color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig
    
    def rq4_subsidy_potential(self):
        """
        Calculates how much 'Extra Revenue' SIRQ generates that could be used as a subsidy.
        """
        pivot = self.df.pivot_table(index="Traffic_Load", columns="Strategy", values="Revenue", aggfunc="mean")
        if "FIFO" in pivot.columns and "SIRQ" in pivot.columns:
            pivot["Subsidy_Pool"] = pivot["SIRQ"] - pivot["FIFO"]
            pivot = pivot.reset_index()
            fig = px.area(pivot, x="Traffic_Load", y="Subsidy_Pool", 
                          title="<b>Societal Benefit:</b> Potential Subsidy Pool ($)",
                          color_discrete_sequence=["#27ae60"])
            fig.update_layout(yaxis_title="Extra Revenue Available for Redistribution ($)", template="plotly_white")
            return fig
        return None