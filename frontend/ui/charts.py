import plotly.graph_objects as go
import pandas as pd

def plot_bollinger_bands(data: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Candlestick price bars
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price',
        increasing_line_color='#3fb950',
        decreasing_line_color='#ff6b6b'
    ))

    # Upper band (red tint)
    fig.add_trace(go.Scatter(
        x=data.index, y=data['upper'],
        line=dict(color='rgba(255,107,107,0.7)', width=1),
        name='Upper Band'
    ))

    # Lower band (green tint) with shaded fill between upper and lower
    fig.add_trace(go.Scatter(
        x=data.index, y=data['lower'],
        line=dict(color='rgba(0,212,170,0.7)', width=1),
        fill='tonexty',
        fillcolor='rgba(120,120,120,0.08)',
        name='Lower Band'
    ))

    # Middle band (dashed white)
    fig.add_trace(go.Scatter(
        x=data.index, y=data['middle'],
        line=dict(color='rgba(255,255,255,0.5)', width=1, dash='dot'),
        name='Middle Band (SMA)'
    ))

    # Buy signals — green triangles pointing up, placed just below lower band
    buys = data[data['signal'] == 1]
    fig.add_trace(go.Scatter(
        x=buys.index,
        y=buys['lower'] * 0.975, #.994
        mode='markers',
        marker=dict(symbol='triangle-up', size=10, color='#00d4aa'),
        name='Buy Signal'
    ))

    # Sell signals — red triangles pointing down, placed just above upper band
    sells = data[data['signal'] == -1]
    fig.add_trace(go.Scatter(
        x=sells.index,
        y=sells['upper'] * 1.02, # 1.006
        mode='markers',
        marker=dict(symbol='triangle-down', size=10, color='#ff6b6b'),
        name='Sell Signal'
    ))

    # Dark theme layout (matches the rest of STRATEX)
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0a0e14',
        plot_bgcolor='#0a0e14',
        title='Bollinger Bands Strategy',
        xaxis_title='Date',
        yaxis_title='Price ($)',
        xaxis_rangeslider_visible=False,
        height=520,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
    )
    
    return fig


from plotly.subplots import make_subplots


def plot_rsi_divergence(data: pd.DataFrame) -> go.Figure:
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.04
    )

    # ── Top panel: Candlestick ──────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price',
        increasing_line_color='#3fb950',
        decreasing_line_color='#ff6b6b'
    ), row=1, col=1)

    # Buy markers on price panel — green triangles below the candle low
    buys = data[data['signal'] == 1]
    fig.add_trace(go.Scatter(
        x=buys.index,
        y=buys['Low'] * 0.993,
        mode='markers',
        marker=dict(symbol='triangle-up', size=10, color='#00d4aa'),
        name='Bullish Divergence'
    ), row=1, col=1)

    # Sell markers on price panel — red triangles above the candle high
    sells = data[data['signal'] == -1]
    fig.add_trace(go.Scatter(
        x=sells.index,
        y=sells['High'] * 1.007,
        mode='markers',
        marker=dict(symbol='triangle-down', size=10, color='#ff6b6b'),
        name='Bearish Divergence'
    ), row=1, col=1)

    # ── Bottom panel: RSI ───────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=data.index, y=data['rsi'],
        line=dict(color='#58a6ff', width=1.5),
        name='RSI'
    ), row=2, col=1)

    # Overbought line at 70
    fig.add_hline(y=70, line=dict(color='rgba(255,107,107,0.6)', width=1, dash='dash'), row=2, col=1)

    # Oversold line at 30
    fig.add_hline(y=30, line=dict(color='rgba(0,212,170,0.6)', width=1, dash='dash'), row=2, col=1)

    # Shaded overbought zone (70–100)
    fig.add_hrect(y0=70, y1=100, fillcolor='rgba(255,107,107,0.06)', line_width=0, row=2, col=1)

    # Shaded oversold zone (0–30)
    fig.add_hrect(y0=0, y1=30, fillcolor='rgba(0,212,170,0.06)', line_width=0, row=2, col=1)

    # Divergence markers mirrored on the RSI panel
    fig.add_trace(go.Scatter(
        x=buys.index,
        y=buys['rsi'],
        mode='markers',
        marker=dict(symbol='triangle-up', size=8, color='#00d4aa'),
        showlegend=False
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=sells.index,
        y=sells['rsi'],
        mode='markers',
        marker=dict(symbol='triangle-down', size=8, color='#ff6b6b'),
        showlegend=False
    ), row=2, col=1)

    # ── Layout ──────────────────────────────────────────────────────────────
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0a0e14',
        plot_bgcolor='#0a0e14',
        title='RSI Divergence Strategy',
        xaxis_title='',
        xaxis2_title='Date',
        yaxis_title='Price ($)',
        yaxis2_title='RSI',
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
        height=600,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
    )

    # Keep RSI y-axis fixed between 0 and 100
    fig.update_yaxes(range=[0, 100], row=2, col=1)

    return fig