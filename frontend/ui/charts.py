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
