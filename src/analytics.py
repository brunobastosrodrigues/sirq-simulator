# src/analytics.py
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

class ScientificPlotter:
    """
    A modular engine to generate publication-ready plots.
    """
    def __init__(self, df):
        self.df = df
        self.colors = {"FIFO": "#3498db", "SIRQ": "#2ecc71"}

    # --- RQ1: ECONOMIC EFFICIENCY ---
    def rq1_revenue_ci(self):
        """Line chart with 95% Confidence Intervals."""
        summary = self.df.groupby(["Traffic_Load", "Strategy"])["Revenue"].agg(["mean", "std", "count"]).reset_index()
        summary['ci'] = 1.96 * (summary['std'] / np.sqrt(summary['count']))
        
        fig = go.Figure()
        for s in self.df["Strategy"].unique():
            sub = summary[summary["Strategy"] == s]
            fig.add_trace(go.Scatter(
                x=sub["Traffic_Load"], y=sub["mean"],
                error_y=dict(type='data', array=sub['ci'], visible=True),
                mode='lines+markers', name=s, line=dict(color=self.colors.get(s, "gray"))
            ))
        fig.update_layout(title="<b>Mean Revenue vs Load</b> (95% CI)", xaxis_title="Traffic Load Multiplier", yaxis_title="Revenue ($)", template="plotly_white")
        return fig

    def rq1_revenue_dist(self):
        """Violin plot to show variance density."""
        fig = px.violin(self.df, x="Traffic_Load", y="Revenue", color="Strategy", box=True, 
                        title="<b>Revenue Distribution Density</b>", color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig

    def rq1_revenue_delta(self):
        """Bar chart showing % improvement of SIRQ over FIFO."""
        pivoted = self.df.pivot_table(index=["Traffic_Load"], columns="Strategy", values="Revenue", aggfunc="mean")
        if "FIFO" in pivoted.columns and "SIRQ" in pivoted.columns:
            pivoted["Delta_Pct"] = ((pivoted["SIRQ"] - pivoted["FIFO"]) / pivoted["FIFO"]) * 100
            pivoted = pivoted.reset_index()
            fig = px.bar(pivoted, x="Traffic_Load", y="Delta_Pct", text_auto='.1f',
                         title="<b>Relative Performance:</b> SIRQ Revenue Gain (%)",
                         color="Delta_Pct", color_continuous_scale="Greens")
            fig.update_layout(yaxis_title="% Improvement over FIFO", template="plotly_white")
            return fig
        return None

    # --- RQ2: CRITICAL RELIABILITY ---
    def rq2_critical_wait_box(self):
        """Box plot of wait times."""
        fig = px.box(self.df, x="Traffic_Load", y="Avg_Wait_Critical", color="Strategy",
                     title="<b>Critical Truck Wait Times</b>", color_discrete_map=self.colors)
        fig.update_layout(yaxis_title="Avg Wait Time (min)", template="plotly_white")
        return fig

    def rq2_failure_rate(self):
        """Rate of failure (Impatient leaving)."""
        fig = px.line(self.df.groupby(["Traffic_Load", "Strategy"])["Critical_Failures"].mean().reset_index(),
                      x="Traffic_Load", y="Critical_Failures", color="Strategy", markers=True,
                      title="<b>System Collapse:</b> Critical Failure Rate", color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig

    def rq2_ecdf_wait(self):
        """Empirical Cumulative Distribution Function (Highly Scientific)."""
        # We need to filter for the highest load to see the stress test
        max_load = self.df["Traffic_Load"].max()
        subset = self.df[self.df["Traffic_Load"] == max_load]
        fig = px.ecdf(subset, x="Avg_Wait_Critical", color="Strategy", 
                      title=f"<b>ECDF of Critical Wait Times</b> (at {max_load}x Load)",
                      color_discrete_map=self.colors)
        fig.update_layout(yaxis_title="Probability (P <= x)", xaxis_title="Wait Time (min)", template="plotly_white")
        return fig

    # --- RQ3: EQUITY ---
    def rq3_equity_gap(self):
        """Line chart showing the widening gap between classes."""
        # Calculate Gap
        self.df["Equity_Gap"] = self.df["Avg_Wait_Economy"] - self.df["Avg_Wait_Critical"]
        summary = self.df.groupby(["Traffic_Load", "Strategy"])["Equity_Gap"].mean().reset_index()
        
        fig = px.line(summary, x="Traffic_Load", y="Equity_Gap", color="Strategy", markers=True,
                      title="<b>The Cost of Priority:</b> Wait Time Gap (Economy - Critical)",
                      color_discrete_map=self.colors)
        fig.update_layout(yaxis_title="Minutes Gap (Positive = Economy waits longer)", template="plotly_white")
        return fig
    
    def rq3_starvation_scatter(self):
        """Scatter plot to check for extreme starvation scenarios."""
        fig = px.scatter(self.df, x="Avg_Wait_Critical", y="Avg_Wait_Economy", color="Strategy", facet_col="Traffic_Load",
                         title="<b>Starvation Analysis:</b> Economy vs Critical Trade-off",
                         opacity=0.6, color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig