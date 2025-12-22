import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

class ScientificPlotter:
    def __init__(self, df):
        self.df = df
        self.colors = {"FIFO": "#3498db", "SIRQ": "#2ecc71"}

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

    def rq2_critical_wait_box(self):
        fig = px.box(self.df, x="Traffic_Load", y="Avg_Wait_Critical", color="Strategy", title="<b>Critical Wait Times</b>", color_discrete_map=self.colors)
        fig.update_layout(yaxis_title="Minutes", template="plotly_white")
        return fig

    def rq2_failure_rate(self):
        fig = px.line(self.df.groupby(["Traffic_Load", "Strategy"])["Critical_Failures"].mean().reset_index(), x="Traffic_Load", y="Critical_Failures", color="Strategy", markers=True, title="<b>Critical Failure Rate</b>", color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig

    def rq2_ecdf_wait(self):
        max_load = self.df["Traffic_Load"].max()
        subset = self.df[self.df["Traffic_Load"] == max_load]
        fig = px.ecdf(subset, x="Avg_Wait_Critical", color="Strategy", title=f"<b>ECDF of Wait Times</b> (Load {max_load}x)", color_discrete_map=self.colors)
        fig.update_layout(yaxis_title="Probability", template="plotly_white")
        return fig

    def rq3_equity_gap(self):
        self.df["Equity_Gap"] = self.df["Avg_Wait_Economy"] - self.df["Avg_Wait_Critical"]
        summary = self.df.groupby(["Traffic_Load", "Strategy"])["Equity_Gap"].mean().reset_index()
        fig = px.line(summary, x="Traffic_Load", y="Equity_Gap", color="Strategy", markers=True, title="<b>Gap: Economy Wait - Critical Wait</b>", color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig
    
    def rq3_starvation_scatter(self):
        fig = px.scatter(self.df, x="Avg_Wait_Critical", y="Avg_Wait_Economy", color="Strategy", facet_col="Traffic_Load", title="<b>Starvation: Economy vs Critical</b>", opacity=0.6, color_discrete_map=self.colors)
        fig.update_layout(template="plotly_white")
        return fig