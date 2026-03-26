"""
STRATEX - Trading Strategy Assistant
Streamlit Frontend
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Configuration
API_BASE = "http://localhost:5000/api"

st.set_page_config(
    page_title="STRATEX - Trading Strategy Assistant",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme styling
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp {
        background-color: #0a0e14;
    }
    
    /* Metric cards */
    .metric-card {
        background: #0d1117;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .metric-value.positive { color: #3fb950; }
    .metric-value.negative { color: #ff6b6b; }
    .metric-value.cyan { color: #00d4aa; }
    
    .metric-label {
        color: #ffffff;
        font-size: 0.875rem;
    }
    
    /* Section headers */
    .section-header {
        color: #e6edf3;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .section-icon {
        color: #00d4aa;
    }
    
    /* Strategy cards */
    .strategy-card {
        background: #151b23;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 8px;
    }
    
    .strategy-name {
        font-weight: 600;
        color: #e6edf3;
    }
    
    .strategy-type {
        color: #ffffff;
        font-size: 0.75rem;
        text-transform: capitalize;
    }
    
    /* SQL code display */
    .sql-display {
        background: #0d1117;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #00d4aa;
        overflow-x: auto;
    }
    
    /* Type badge */
    .type-badge {
        display: inline-block;
        padding: 4px 8px;
        background: #1a222d;
        border-radius: 4px;
        font-size: 0.75rem;
        color: #8b949e;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #0d1117;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# API HELPER FUNCTIONS
# =============================================================================

@st.cache_data(ttl=60)
def fetch_templates():
    try:
        response = requests.get(f"{API_BASE}/templates")
        return response.json()
    except:
        return {}

@st.cache_data(ttl=60)
def fetch_symbols():
    try:
        response = requests.get(f"{API_BASE}/symbols")
        return response.json()
    except:
        return []

@st.cache_data(ttl=10)
def fetch_strategies():
    try:
        response = requests.get(f"{API_BASE}/strategies")
        return response.json()
    except:
        return []

@st.cache_data(ttl=10)
def fetch_dashboard_summary():
    try:
        response = requests.get(f"{API_BASE}/reports/dashboard-summary")
        return response.json()
    except:
        return {}

def run_backtest(config):
    try:
        response = requests.post(f"{API_BASE}/backtest", json=config)
        return response.json()
    except Exception as e:
        st.error(f"Backtest failed: {e}")
        return None

def save_strategy(strategy):
    try:
        response = requests.post(f"{API_BASE}/strategies", json=strategy)
        return response.json()
    except Exception as e:
        st.error(f"Failed to save strategy: {e}")
        return None

def delete_strategy(strategy_id):
    try:
        response = requests.delete(f"{API_BASE}/strategies/{strategy_id}")
        return response.status_code == 204
    except:
        return False

@st.cache_data(ttl=30)
def fetch_report(endpoint):
    try:
        response = requests.get(f"{API_BASE}{endpoint}")
        return response.json()
    except:
        return []


# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================

with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span style="font-size: 1.5rem; color: #00d4aa;">◈</span>
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; font-weight: 700; letter-spacing: 0.1em;">STRATEX</span>
    </div>
    <p style="color: #ffffff; font-size: 0.875rem; margin-bottom: 2rem;">Trading Strategy Assistant</p>
    """, unsafe_allow_html=True)
    
    page = st.radio(
        "Navigation",
        ["◉ Dashboard", "⚡ Strategy Builder", "◫ Strategy Library", "◈ Backtest Results", "◇ SQL Reports"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("""
    <p style="color: #ffffff; font-size: 0.75rem; text-align: center;">
        Built with Flask + Streamlit<br>SQL-Powered Analytics
    </p>
    """, unsafe_allow_html=True)


# =============================================================================
# DASHBOARD PAGE
# =============================================================================

if page == "◉ Dashboard":
    st.title("Dashboard")
    st.markdown("Overview of your trading strategy performance")
    
    summary = fetch_dashboard_summary()
    strategies = fetch_strategies()
    
    # Stats Grid
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Strategies", summary.get('active_strategies', 0))
    with col2:
        st.metric("Total Backtests", summary.get('total_backtests', 0))
    with col3:
        st.metric("Symbols Tested", summary.get('symbols_tested', 0))
    with col4:
        st.metric("Total Trades", f"{summary.get('total_trades', 0):,}")
    
    # Performance Metrics
    st.markdown("---")
    st.subheader("Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    avg_return = summary.get('avg_return', 0)
    with col1:
        st.metric("Avg Return", f"{avg_return:+.1f}%", delta_color="normal")
    
    with col2:
        st.metric("Best Return", f"{summary.get('best_return', 0):+.1f}%")
    
    with col3:
        st.metric("Avg Sharpe", f"{summary.get('avg_sharpe', 0):.2f}")
    
    with col4:
        st.metric("Avg Win Rate", f"{summary.get('avg_win_rate', 0):.1f}%")
    
    # Recent Strategies
    if strategies:
        st.markdown("---")
        st.subheader("Recent Strategies")
        
        for strategy in strategies[:5]:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{strategy['name']}**")
                st.caption(strategy['strategy_type'].replace('_', ' ').title())
            with col2:
                st.caption(strategy['created_at'][:10])
            st.markdown("---")
    
    # Empty state
    if not summary or summary.get('total_backtests', 0) == 0:
        st.info("No backtests yet. Create a strategy and run your first backtest to see performance data here.")


# =============================================================================
# STRATEGY BUILDER PAGE
# =============================================================================

elif page == "⚡ Strategy Builder":
    st.title("Strategy Builder")
    st.markdown("Configure and backtest trading strategies using pre-built templates")
    
    templates = fetch_templates()
    symbols = fetch_symbols()
    
    if not templates:
        st.error("Could not load templates. Is the backend running?")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("◈ Strategy Template")
            
            template_names = {k: v['name'] for k, v in templates.items()}
            selected_template = st.selectbox(
                "Select Strategy Type",
                options=list(templates.keys()),
                format_func=lambda x: templates[x]['name']
            )
            
            template = templates[selected_template]
            st.info(template['description'])
            
            strategy_name = st.text_input("Strategy Name", value=f"{template['name']} Strategy")
            description = st.text_area("Description", value=template['description'], height=100)
        
        with col2:
            st.subheader("⚡ Parameters")
            
            parameters = {}
            for key, config in template['parameters'].items():
                if config['type'] == 'select':
                    parameters[key] = st.selectbox(
                        config['description'],
                        options=config['options'],
                        index=config['options'].index(config['default'])
                    )
                elif config['type'] == 'int':
                    parameters[key] = st.slider(
                        config['description'],
                        min_value=config['min'],
                        max_value=config['max'],
                        value=config['default']
                    )
                elif config['type'] == 'float':
                    parameters[key] = st.slider(
                        config['description'],
                        min_value=float(config['min']),
                        max_value=float(config['max']),
                        value=float(config['default']),
                        step=0.1
                    )
            
            st.subheader("◇ Backtest Settings")
            
            symbol = st.selectbox("Symbol", options=symbols if symbols else ['SPY'])
            initial_capital = st.number_input("Initial Capital ($)", value=10000, min_value=1000, step=1000)
            
            col_start, col_end = st.columns(2)
            with col_start:
                start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=730))
            with col_end:
                end_date = st.date_input("End Date", value=datetime.now())
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            save_strategy_checkbox = st.checkbox("Save strategy to library", value=True)
        with col3:
            run_button = st.button("▶ Run Backtest", type="primary", use_container_width=True)
        
        if run_button:
            with st.spinner("Running backtest..."):
                strategy_id = None
                
                if save_strategy_checkbox:
                    saved = save_strategy({
                        'name': strategy_name,
                        'description': description,
                        'strategy_type': selected_template,
                        'parameters': parameters
                    })
                    if saved:
                        strategy_id = saved.get('id')
                        st.success("Strategy saved!")
                
                result = run_backtest({
                    'strategy_id': strategy_id,
                    'strategy_type': selected_template,
                    'parameters': parameters,
                    'symbol': symbol,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'initial_capital': initial_capital
                })
                
                if result:
                    st.session_state['backtest_result'] = result
                    st.success(f"Backtest completed in {result.get('execution_time_ms', 0)}ms! Go to Backtest Results to view.")
                    st.cache_data.clear()

    # =========================================================================
    # BOLLINGER BANDS STRATEGY
    # =========================================================================
    st.markdown("---")
    st.subheader("Bollinger Bands Strategy")
    st.markdown(
        "Trade mean-reversion signals using Bollinger Bands: "
        "buy when price touches the lower band and sell when it reaches the upper band."
    )

    bb_left, bb_right = st.columns(2)

    with bb_left:
        bb_symbol = st.text_input("Symbol", value="SPY", key="bb_symbol")
        bb_start = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=730),
            key="bb_start",
        )
        bb_end = st.date_input(
            "End Date",
            value=datetime.now(),
            key="bb_end",
        )

    with bb_right:
        bb_window = st.slider(
            "Window (periods)",
            min_value=5,
            max_value=50,
            value=20,
            key="bb_window",
        )
        bb_std = st.slider(
            "Std Dev Multiplier",
            min_value=1.0,
            max_value=3.0,
            value=2.0,
            step=0.1,
            key="bb_std",
        )
        bb_capital = st.number_input(
            "Initial Capital ($)",
            value=10000,
            min_value=1000,
            step=1000,
            key="bb_capital",
        )

    if st.button("Run Bollinger Bands", type="primary", key="bb_run"):
        try:
            import sys, os
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

            from backend.data.fetcher import fetch_ohlcv
            from backend.strategies.bollinger_bands import BollingerBandsStrategy
            from frontend.ui.charts import plot_bollinger_bands

        except ImportError as e:
            st.error(f"Could not import a required module: {e}")
            st.stop()

        with st.spinner(f"Fetching {bb_symbol.upper()} data…"):
            try:
                df = fetch_ohlcv(
                    bb_symbol.strip().upper(),
                    bb_start.isoformat(),
                    bb_end.isoformat(),
                )
            
            except NotImplementedError:
                st.error("fetcher.fetch_ohlcv() is not implemented yet.")
                st.stop()

        if df.empty:
            st.error(
                f"No data returned for **{bb_symbol.upper()}**. "
                "Check the symbol or widen the date range."
            )
        else:
            try:
                strategy = BollingerBandsStrategy(window=bb_window, num_std=bb_std)
                signals_df = strategy.generate_signals(df)
            except NotImplementedError:
                st.error("BollingerBandsStrategy.generate_signals() is not implemented yet.")
                st.stop()
            except Exception as e:
                st.error(f"Signal generation failed: {e}")
                st.stop()

            # ── Save for backtesting team ──────────────────────────────
            st.session_state["bb_signals"] = signals_df

            # ── Metrics ───────────────────────────────────────────────
            buy_signals  = int((signals_df["signal"] == 1).sum())
            sell_signals = int((signals_df["signal"] == -1).sum())

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Symbol", bb_symbol.upper())
            with m2:
                st.metric("Data Points", len(signals_df))
            with m3:
                st.metric("Buy Signals",  buy_signals)
            with m4:
                st.metric("Sell Signals", sell_signals)

            # ── Chart ─────────────────────────────────────────────────
            st.markdown("---")
            fig = plot_bollinger_bands(signals_df)
            st.plotly_chart(fig, use_container_width=True)



# =============================================================================
# STRATEGY LIBRARY PAGE
# =============================================================================

elif page == "◫ Strategy Library":
    st.title("Strategy Library")
    st.markdown("Manage and backtest your saved trading strategies")
    
    strategies = fetch_strategies()
    symbols = fetch_symbols()
    templates = fetch_templates()
    
    if not strategies:
        st.info("No strategies saved yet. Create a strategy in the Strategy Builder.")
    else:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Saved Strategies")
            
            strategy_options = {s['id']: s['name'] for s in strategies}
            selected_id = st.radio(
                "Select a strategy",
                options=list(strategy_options.keys()),
                format_func=lambda x: strategy_options[x],
                label_visibility="collapsed"
            )
            
            selected_strategy = next((s for s in strategies if s['id'] == selected_id), None)
        
        with col2:
            if selected_strategy:
                st.subheader(selected_strategy['name'])
                st.caption(templates.get(selected_strategy['strategy_type'], {}).get('name', selected_strategy['strategy_type']))
                
                if selected_strategy.get('description'):
                    st.markdown(selected_strategy['description'])
                
                st.markdown("**Parameters:**")
                params_df = pd.DataFrame([
                    {"Parameter": k.replace('_', ' ').title(), "Value": v}
                    for k, v in selected_strategy['parameters'].items()
                ])
                st.dataframe(params_df, hide_index=True, use_container_width=True)
                
                st.markdown("---")
                st.markdown("**Run Backtest:**")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    lib_symbol = st.selectbox("Symbol", options=symbols if symbols else ['SPY'], key="lib_symbol")
                    lib_start = st.date_input("Start Date", value=datetime.now() - timedelta(days=730), key="lib_start")
                with col_b:
                    lib_capital = st.number_input("Initial Capital ($)", value=10000, min_value=1000, step=1000, key="lib_capital")
                    lib_end = st.date_input("End Date", value=datetime.now(), key="lib_end")
                
                col_run, col_del = st.columns(2)
                with col_run:
                    if st.button("▶ Run Backtest", type="primary", use_container_width=True, key="lib_run"):
                        with st.spinner("Running backtest..."):
                            result = run_backtest({
                                'strategy_id': selected_strategy['id'],
                                'symbol': lib_symbol,
                                'start_date': lib_start.isoformat(),
                                'end_date': lib_end.isoformat(),
                                'initial_capital': lib_capital
                            })
                            if result:
                                st.session_state['backtest_result'] = result
                                st.success("Backtest completed! Go to Backtest Results to view.")
                                st.cache_data.clear()
                
                with col_del:
                    if st.button("🗑 Delete Strategy", use_container_width=True, key="lib_del"):
                        if delete_strategy(selected_strategy['id']):
                            st.success("Strategy deleted!")
                            st.cache_data.clear()
                            st.rerun()
                
                st.caption(f"Created: {selected_strategy['created_at'][:10]}")


# =============================================================================
# BACKTEST RESULTS PAGE
# =============================================================================

elif page == "◈ Backtest Results":
    st.title("Backtest Results")
    
    result = st.session_state.get('backtest_result')
    
    if not result:
        st.info("No results yet. Configure and run a backtest from the Strategy Builder or Library to see results here.")
    else:
        st.caption(f"Executed in {result.get('execution_time_ms', 0)}ms")
        
        # Metrics Grid
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Return", f"{result['total_return']:+.2f}%")
            st.metric("Win Rate", f"{result['win_rate']:.1f}%")
        with col2:
            st.metric("Annualized Return", f"{result['annualized_return']:+.2f}%")
            st.metric("Total Trades", result['total_trades'])
        with col3:
            st.metric("Sharpe Ratio", f"{result['sharpe_ratio']:.2f}")
            st.metric("Profit Factor", f"{result['profit_factor']:.2f}")
        with col4:
            st.metric("Max Drawdown", f"{result['max_drawdown']:.2f}%")
            st.metric("Avg Trade Return", f"{result['avg_trade_return']:+.2f}%")
        
        st.markdown("---")
        
        # Charts
        tab1, tab2, tab3 = st.tabs(["📈 Equity Curve", "📉 Drawdown", "📊 Monthly Returns"])
        
        with tab1:
            if result.get('equity_curve'):
                df = pd.DataFrame(result['equity_curve'])
                df['date'] = pd.to_datetime(df['date'])
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['equity'],
                    mode='lines',
                    fill='tozeroy',
                    line=dict(color='#00d4aa', width=2),
                    fillcolor='rgba(0, 212, 170, 0.1)'
                ))
                fig.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='#0a0e14',
                    plot_bgcolor='#0a0e14',
                    xaxis_title='Date',
                    yaxis_title='Portfolio Value ($)',
                    height=400,
                    margin=dict(l=0, r=0, t=20, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            if result.get('drawdown_curve'):
                df = pd.DataFrame(result['drawdown_curve'])
                df['date'] = pd.to_datetime(df['date'])
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['drawdown'],
                    mode='lines',
                    fill='tozeroy',
                    line=dict(color='#ff6b6b', width=2),
                    fillcolor='rgba(255, 107, 107, 0.1)'
                ))
                fig.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='#0a0e14',
                    plot_bgcolor='#0a0e14',
                    xaxis_title='Date',
                    yaxis_title='Drawdown (%)',
                    height=400,
                    margin=dict(l=0, r=0, t=20, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            if result.get('monthly_returns'):
                df = pd.DataFrame(result['monthly_returns'])
                
                colors = ['#00d4aa' if x >= 0 else '#ff6b6b' for x in df['return']]
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df['month'],
                    y=df['return'],
                    marker_color=colors
                ))
                fig.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='#0a0e14',
                    plot_bgcolor='#0a0e14',
                    xaxis_title='Month',
                    yaxis_title='Return (%)',
                    height=400,
                    margin=dict(l=0, r=0, t=20, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Trade History
        st.markdown("---")
        st.subheader("Trade History")
        
        if result.get('trades'):
            trades_df = pd.DataFrame(result['trades'])
            trades_df['return_pct'] = trades_df['return_pct'].apply(lambda x: f"{x:+.2f}%")
            trades_df['profit'] = trades_df['profit'].apply(lambda x: f"${x:+.2f}")
            trades_df['entry_price'] = trades_df['entry_price'].apply(lambda x: f"${x:.2f}")
            trades_df['exit_price'] = trades_df['exit_price'].apply(lambda x: f"${x:.2f}")
            
            trades_df = trades_df.rename(columns={
                'entry_date': 'Entry Date',
                'exit_date': 'Exit Date',
                'entry_price': 'Entry Price',
                'exit_price': 'Exit Price',
                'return_pct': 'Return',
                'profit': 'Profit'
            })
            
            st.dataframe(trades_df, hide_index=True, use_container_width=True)
        
        # Additional Stats
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Winning Streaks")
            st.metric("Max Consecutive Wins", result.get('max_consecutive_wins', 0))
            st.metric("Max Consecutive Losses", result.get('max_consecutive_losses', 0))
        
        with col2:
            st.subheader("Trade Breakdown")
            profitable = result.get('profitable_trades', 0)
            total = result.get('total_trades', 1)
            losing = total - profitable
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[profitable],
                y=['Trades'],
                orientation='h',
                name='Winners',
                marker_color='#00d4aa'
            ))
            fig.add_trace(go.Bar(
                x=[losing],
                y=['Trades'],
                orientation='h',
                name='Losers',
                marker_color='#ff6b6b'
            ))
            fig.update_layout(
                barmode='stack',
                template='plotly_dark',
                paper_bgcolor='#0a0e14',
                plot_bgcolor='#0a0e14',
                height=100,
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# SQL REPORTS PAGE
# =============================================================================

elif page == "◇ SQL Reports":
    st.title("SQL Reports")
    st.markdown("Advanced analytics powered by complex SQL queries")
    
    report_options = {
        'Strategy Comparison': '/reports/strategy-comparison',
        'Performance by Symbol': '/reports/performance-by-symbol',
        'Time Analysis': '/reports/time-analysis',
        'Top Performers': '/reports/top-performers',
        'Risk Metrics': '/reports/risk-metrics'
    }
    
    sql_queries = {
        'Strategy Comparison': """SELECT 
    s.name as strategy_name,
    s.strategy_type,
    COUNT(b.id) as total_backtests,
    AVG(b.total_return) as avg_return,
    AVG(b.sharpe_ratio) as avg_sharpe,
    AVG(b.max_drawdown) as avg_max_drawdown,
    MAX(b.total_return) as best_return,
    MIN(b.total_return) as worst_return
FROM strategies s
LEFT JOIN backtests b ON s.id = b.strategy_id
GROUP BY s.id, s.name, s.strategy_type
HAVING COUNT(b.id) > 0
ORDER BY avg_return DESC""",
        'Performance by Symbol': """SELECT 
    b.symbol,
    s.strategy_type,
    COUNT(b.id) as backtest_count,
    AVG(b.total_return) as avg_return,
    AVG(b.sharpe_ratio) as avg_sharpe,
    SUM(CASE WHEN b.total_return > 0 THEN 1 ELSE 0 END) as profitable_runs
FROM backtests b
JOIN strategies s ON b.strategy_id = s.id
GROUP BY b.symbol, s.strategy_type
ORDER BY b.symbol, avg_return DESC""",
        'Time Analysis': """SELECT 
    strftime('%Y-%m', b.executed_at) as month,
    COUNT(b.id) as backtests_run,
    AVG(b.total_return) as avg_return,
    AVG(b.sharpe_ratio) as avg_sharpe,
    SUM(b.total_trades) as total_trades
FROM backtests b
GROUP BY strftime('%Y-%m', b.executed_at)
ORDER BY month DESC
LIMIT 12""",
        'Top Performers': """SELECT 
    b.id, s.name, b.symbol,
    b.total_return, b.sharpe_ratio,
    b.max_drawdown, b.win_rate,
    b.total_trades
FROM backtests b
JOIN strategies s ON b.strategy_id = s.id
ORDER BY b.total_return DESC
LIMIT 10""",
        'Risk Metrics': """SELECT 
    s.strategy_type,
    COUNT(b.id) as sample_size,
    AVG(b.max_drawdown) as avg_drawdown,
    MIN(b.max_drawdown) as worst_drawdown,
    AVG(b.sharpe_ratio) as avg_sharpe,
    AVG(b.total_return / NULLIF(ABS(b.max_drawdown), 0)) as return_to_drawdown
FROM backtests b
JOIN strategies s ON b.strategy_id = s.id
GROUP BY s.strategy_type
ORDER BY avg_sharpe DESC"""
    }
    
    selected_report = st.selectbox("Select Report", options=list(report_options.keys()))
    
    # SQL Display
    st.markdown("**SQL Query:**")
    st.code(sql_queries[selected_report], language='sql')
    
    # Fetch and display report
    st.markdown("---")
    
    data = fetch_report(report_options[selected_report])
    
    if not data:
        st.info("No data available. Run some backtests first!")
    else:
        df = pd.DataFrame(data)
        
        # Format numeric columns
        for col in df.columns:
            if 'return' in col.lower() or 'drawdown' in col.lower() or 'sharpe' in col.lower():
                if df[col].dtype in ['float64', 'int64']:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")
        
        st.dataframe(df, hide_index=True, use_container_width=True)
        
        # Additional visualizations for certain reports
        if selected_report == 'Strategy Comparison' and len(data) > 0:
            st.markdown("---")
            st.subheader("Visual Comparison")
            
            chart_df = pd.DataFrame(data)
            fig = px.bar(
                chart_df,
                x='strategy_name',
                y='avg_return',
                color='avg_return',
                color_continuous_scale=['#ff6b6b', '#ffd93d', '#00d4aa'],
                title='Average Return by Strategy'
            )
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='#0a0e14',
                plot_bgcolor='#0a0e14'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        if selected_report == 'Risk Metrics' and len(data) > 0:
            st.markdown("---")
            st.subheader("Risk Analysis")
            
            chart_df = pd.DataFrame(data)
            fig = px.scatter(
                chart_df,
                x='avg_drawdown',
                y='avg_sharpe',
                size='sample_size',
                color='strategy_type',
                title='Risk vs Reward by Strategy Type'
            )
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='#0a0e14',
                plot_bgcolor='#0a0e14'
            )
            st.plotly_chart(fig, use_container_width=True)
