import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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