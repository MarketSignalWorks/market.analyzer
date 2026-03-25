import plotly.graph_objects as go
import pandas as pd

def plot_bollinger_bands(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # --- Shaded band fill (upper → lower) ---
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Upper"],
        name="Upper Band",
        line=dict(color="rgba(255,107,107,0.5)", width=1, dash="dot"),
        fill=None,
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Lower"],
        name="Lower Band",
        line=dict(color="rgba(63,185,80,0.5)", width=1, dash="dot"),
        fill="tonexty",
        fillcolor="rgba(0,212,170,0.06)",
    ))

    # --- Middle band (SMA) ---
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Middle"],
        name="Middle Band (SMA)",
        line=dict(color="rgba(139,148,158,0.9)", width=1, dash="dash"),
    ))

    # --- Close price ---
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        name="Close",
        line=dict(color="#00d4aa", width=2),
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0e14",
        plot_bgcolor="#0a0e14",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=450,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        hovermode="x unified",
    )
    return fig
