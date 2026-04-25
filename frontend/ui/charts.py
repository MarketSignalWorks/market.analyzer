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

def plot_macd_crossover(data: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.03
    )
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

    ema_valid = data['ema_200'].dropna()
    fig.add_trace(go.Scatter(
        x=ema_valid.index,
        y=ema_valid,
        name='200 EMA',
        mode='lines',
        line=dict(color='#f0c040', width=1.5, dash='dot')
    ), row=1, col=1)

    if 'regime' in data.columns:
        regime = data['regime']
        in_choppy = False
        block_start = None

        for i, (idx, val) in enumerate(regime.items()):
            if val == 1 and not in_choppy:
                in_choppy = True
                block_start = idx
            elif val != 1 and in_choppy:
                in_choppy = False
                fig.add_vrect(
                    x0=block_start, x1=idx,
                    fillcolor='gray', opacity=0.10,
                    layer='below', line_width=0,
                    row=1, col=1
                )
        if in_choppy:
            fig.add_vrect(
                x0=block_start, x1=data.index[-1],
                fillcolor='gray', opacity=0.10,
                layer='below', line_width=0,
                row=1, col=1
            )

    buys = data[data['signal'] == 1]
    has_confidence = 'confidence' in data.columns

    buy_text = []
    if has_confidence:
        for idx in buys.index:
            conf = buys.loc[idx, 'confidence']
            buy_text.append(f'{conf:.2f}' if conf != 0.0 else '')
    else:
        buy_text = ['' for _ in buys.index]

    fig.add_trace(go.Scatter(
        x=buys.index,
        y=buys['Low'] * 0.993,
        mode='markers+text',
        marker=dict(symbol='triangle-up', size=10, color='#00d4aa'),
        text=buy_text,
        textposition='bottom center',
        textfont=dict(size=9, color='#00d4aa'),
        name='Buy Signal'
    ), row=1, col=1)

    sells = data[data['signal'] == -1]

    sell_text = []
    if has_confidence:
        for idx in sells.index:
            conf = sells.loc[idx, 'confidence']
            sell_text.append(f'{conf:.2f}' if conf != 0.0 else '')
    else:
        sell_text = ['' for _ in sells.index]

    fig.add_trace(go.Scatter(
        x=sells.index,
        y=sells['High'] * 1.007,
        mode='markers+text',
        marker=dict(symbol='triangle-down', size=10, color='#ff6b6b'),
        text=sell_text,
        textposition='top center',
        textfont=dict(size=9, color='#ff6b6b'),
        name='Sell Signal'
    ), row=1, col=1)


    hist = data['histogram']
    pos_hist = hist.where(hist > 0)
    neg_hist = hist.where(hist < 0)

    fig.add_trace(go.Bar(
        x=data.index,
        y=pos_hist,
        marker_color='rgba(0,200,100,0.6)',
        name='Histogram (+)',
        showlegend=True
    ), row=2, col=1)

    fig.add_trace(go.Bar(
        x=data.index,
        y=neg_hist,
        marker_color='rgba(220,50,50,0.6)',
        name='Histogram (−)',
        showlegend=True
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=data['macd'],
        line=dict(color='#00b4d8', width=1.5),
        name='MACD'
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=data['signal_line'],
        line=dict(color='#f4a261', width=1.5),
        name='Signal Line'
    ), row=2, col=1)

    fig.add_hline(y=0, line_dash='dash', line_color='gray', row=2, col=1)

    fig.add_trace(go.Scatter(
        x=buys.index,
        y=buys['macd'],
        mode='markers',
        marker=dict(symbol='triangle-up', size=8, color='#00d4aa'),
        showlegend=False
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=sells.index,
        y=sells['macd'],
        mode='markers',
        marker=dict(symbol='triangle-down', size=8, color='#ff6b6b'),
        showlegend=False
    ), row=2, col=1)

    title = f"MACD Crossover — {data.index[0].date()} to {data.index[-1].date()}"

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0a0e14',
        plot_bgcolor='#0a0e14',
        title=title,
        yaxis_title='Price ($)',
        yaxis2_title='MACD',
        height=700,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        barmode='overlay'
    )

    fig.update_xaxes(rangeslider_visible=False)

    return fig

def plot_vwap_reversion(data: pd.DataFrame) -> go.Figure:

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.65, 0.35],
        shared_xaxes=True,
        vertical_spacing=0.03
    )

    # Panel 1: Candlestick
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

    fig.add_trace(go.Scatter(
        x=data.index, y=data['vwap'],
        line=dict(color='#a78bfa', width=2),
        name='VWAP'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=data['upper_band'],
        line=dict(color='rgba(167,139,250,0.4)', width=1, dash='dot'),
        name='Upper Band'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=data['lower_band'],
        line=dict(color='rgba(167,139,250,0.4)', width=1, dash='dot'),
        name='Lower Band'
    ), row=1, col=1)

    entries = data[(data['signal'].diff() != 0) & (data['signal'] != 0)]

    long_entries  = entries[entries['signal'] == 1]
    short_entries = entries[entries['signal'] == -1]

    fig.add_trace(go.Scatter(
        x=long_entries.index,
        y=long_entries['Low'] * 0.993,
        mode='markers',
        marker=dict(symbol='triangle-up', size=10, color='#3fb950'),
        name='Long Entry'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=short_entries.index,
        y=short_entries['High'] * 1.007,
        mode='markers',
        marker=dict(symbol='triangle-down', size=10, color='#ff6b6b'),
        name='Short Entry'
    ), row=1, col=1)

    # Panel 2: Volume
    green_mask = data['Close'] > data['Open']
    vol_colors = [
        'rgba(63,185,80,0.6)' if g else 'rgba(255,107,107,0.6)'
        for g in green_mask
    ]

    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Volume'],
        marker_color=vol_colors,
        name='Volume',
        showlegend=True
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=data['avg_volume'],
        line=dict(color='#f0c040', width=1.5, dash='dot'),
        name='Avg Volume'
    ), row=2, col=1)

    spike_mask = (data['volume_ratio'] > data['volume_multiplier']) & (data['signal'] != 0)
    spikes = data[spike_mask]

    fig.add_trace(go.Scatter(
        x=spikes.index,
        y=spikes['Volume'] * 1.05,
        mode='markers',
        marker=dict(symbol='star', size=8, color='#f0c040'),
        name='Vol Spike'
    ), row=2, col=1)

    # Layout
    title = f"VWAP Reversion — {data.index[0].date()} to {data.index[-1].date()}"

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0a0e14',
        plot_bgcolor='#0a0e14',
        title=title,
        yaxis_title='Price ($)',
        yaxis2_title='Volume',
        height=700,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        barmode='overlay'
    )

    fig.update_xaxes(rangeslider_visible=False)

    return fig