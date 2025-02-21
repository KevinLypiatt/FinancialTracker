import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import time
from utils import get_delta_color, format_percentage
from market_data import MarketDataFetcher
import plotly.graph_objects as go
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Page config
st.set_page_config(
    page_title="Financial Markets Dashboard",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .data-card {
        padding: 20px;
        border-radius: 10px;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)

def get_historical_data():
    """Fetch the last two days of data from Supabase"""
    try:
        response = supabase.table('financial_data').select('*').order('timestamp', desc=True).limit(2).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return None
    except Exception as e:
        st.error(f"Error fetching historical data: {str(e)}")
        return None

def calculate_change(current, previous, field):
    """Calculate percentage change between current and previous values"""
    if previous is None or current is None:
        return 0.0
    if field not in previous or field not in current:
        return 0.0
    prev_value = previous[field]
    curr_value = current[field]
    if prev_value and curr_value and prev_value != 0:
        return ((curr_value - prev_value) / prev_value) * 100
    return 0.0

def create_yield_curve_chart(data):
    maturities = [2, 5, 10, 30]
    yields = [
        data['us_2y_yield'],
        data['us_5y_yield'],
        data['us_10y_yield'],
        data['us_30y_yield']
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=maturities,
        y=yields,
        mode='lines+markers',
        name='Yield Curve',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=8)
    ))

    fig.update_layout(
        title='US Treasury Yield Curve',
        xaxis_title='Maturity (Years)',
        yaxis_title='Yield (%)',
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def main():
    st.title("📈 Financial Markets Dashboard")

    # Get historical data
    hist_data = get_historical_data()

    # Initialize market data fetcher
    market_fetcher = MarketDataFetcher()

    # Get current data
    current_data = market_fetcher.get_market_data()

    # Get previous day's data
    previous_data = hist_data.iloc[1].to_dict() if hist_data is not None and len(hist_data) > 1 else None

    # Display last update time
    st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # Create three columns for the main indicators
    col1, col2, col3 = st.columns(3)

    # Gold (USD)
    with col1:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.metric(
            "Gold (USD)",
            f"${current_data['gold_usd']:,.2f}",
            format_percentage(calculate_change(current_data, previous_data, 'gold_usd')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'gold_usd'))
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Gold (GBP)
    with col2:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.metric(
            "Gold (GBP)",
            f"£{current_data['gold_gbp']:,.2f}",
            format_percentage(calculate_change(current_data, previous_data, 'gold_gbp')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'gold_gbp'))
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # GBP/USD
    with col3:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.metric(
            "GBP/USD",
            f"{current_data['gbp_usd']:.4f}",
            format_percentage(calculate_change(current_data, previous_data, 'gbp_usd')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'gbp_usd'))
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Create two columns for S&P 500 and Bitcoin
    col4, col5 = st.columns(2)

    # S&P 500
    with col4:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.metric(
            "S&P 500",
            f"{current_data['sp500']:,.2f}",
            format_percentage(calculate_change(current_data, previous_data, 'sp500')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'sp500'))
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Bitcoin
    with col5:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.metric(
            "Bitcoin (USD)",
            f"${current_data['bitcoin']:,.2f}",
            format_percentage(calculate_change(current_data, previous_data, 'bitcoin')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'bitcoin'))
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Yield Curve Section
    st.subheader("US Treasury Yield Curve")

    # Display yield curve chart
    yield_curve_fig = create_yield_curve_chart(current_data)
    st.plotly_chart(yield_curve_fig, use_container_width=True)

    # Individual yield metrics
    yield_cols = st.columns(4)

    yields = [
        ("2Y Yield", 'us_2y_yield'),
        ("5Y Yield", 'us_5y_yield'),
        ("10Y Yield", 'us_10y_yield'),
        ("30Y Yield", 'us_30y_yield')
    ]

    for col, (label, key) in zip(yield_cols, yields):
        with col:
            st.markdown("<div class='data-card'>", unsafe_allow_html=True)
            st.metric(
                label,
                f"{current_data[key]:.2f}%",
                format_percentage(calculate_change(current_data, previous_data, key)),
                delta_color=get_delta_color(calculate_change(current_data, previous_data, key))
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # Refresh every minute
    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()