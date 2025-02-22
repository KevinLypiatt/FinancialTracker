import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import time
from utils import get_delta_color, format_percentage
from market_data import MarketDataFetcher
import plotly.graph_objects as go
from supabase import create_client, Client
from typing import Optional
import os
from dotenv import load_dotenv
from notification_manager import NotificationManager
import logging
import pathlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize NotificationManager
notification_manager = NotificationManager()
logger.info("NotificationManager initialized")

# Initialize Supabase client
def init_supabase() -> Optional[Client]:
    """Initialize Supabase client with proper error handling"""
    try:
        logger.info("Attempting to connect to Supabase...")
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            logger.error("Supabase credentials not found in environment")
            st.error("Database connection failed: Missing credentials")
            return None

        client = create_client(supabase_url, supabase_key)
        logger.info("Successfully initialized Supabase client")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        st.error(f"Database connection failed: {str(e)}")
        return None

supabase = init_supabase()

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
    [data-testid="stMetricDelta"] > div {
        color: black !important;
    }
    [data-testid="stMetricDelta"][data-direction="down"] > div {
        color: black !important;
    }
    .metric-box {
        background-color: white;
        padding: 10px;
        border-radius: 5px;
        margin: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

def get_historical_data():
    """Fetch the last two days of data from Supabase"""
    try:
        if not supabase:
            logger.error("Cannot fetch historical data: Supabase client not initialized")
            return None

        logger.info("Fetching historical data from Supabase...")
        response = supabase.table('financial_data').select('*').order('timestamp', desc=True).limit(2).execute()

        if response.data:
            logger.info(f"Successfully fetched {len(response.data)} records")
            return pd.DataFrame(response.data)
        logger.warning("No historical data found")
        return None
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        st.error(f"Failed to fetch market data: {str(e)}")
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

    # Initialize market data fetcher
    market_fetcher = MarketDataFetcher()

    # Get current data
    current_data = market_fetcher.get_market_data()

    # Get historical data
    hist_data = get_historical_data()

    # Get previous day's data
    previous_data = hist_data.iloc[1].to_dict() if hist_data is not None and len(hist_data) > 1 else None

    # Check for significant changes and send notifications
    # Only check notifications every 15 minutes to avoid spam
    if int(time.time()) % 900 == 0:  # 900 seconds = 15 minutes
        notification_manager.check_and_notify(current_data, previous_data)

    # Display last update time
    st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # Create three columns for the main indicators
    col1, col2, col3 = st.columns(3)

    # Gold (USD)
    with col1:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.metric(
            "Gold (USD)",
            f"${int(current_data['gold_usd']):,}",
            format_percentage(calculate_change(current_data, previous_data, 'gold_usd')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'gold_usd'))
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Gold (GBP)
    with col2:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.metric(
            "Gold (GBP)",
            f"£{int(current_data['gold_gbp']):,}",
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
            f"{int(current_data['sp500']):,}",
            format_percentage(calculate_change(current_data, previous_data, 'sp500')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'sp500'))
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Bitcoin
    with col5:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.metric(
            "Bitcoin (USD)",
            f"${int(current_data['bitcoin']):,}",
            format_percentage(calculate_change(current_data, previous_data, 'bitcoin')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'bitcoin'))
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Create two columns for UK and US Rates
    st.subheader("Economic Indicators")
    uk_col, us_col = st.columns(2)

    # UK Rates
    with uk_col:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.markdown("### UK Rates")

        # UK Base Rate
        st.metric(
            "Base Rate",
            f"{current_data['uk_base_rate']:.2f}%" if current_data['uk_base_rate'] else "N/A",
            format_percentage(calculate_change(current_data, previous_data, 'uk_base_rate')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'uk_base_rate'))
        )

        # UK Inflation
        st.metric(
            "Inflation Rate",
            f"{current_data['uk_inflation']:.2f}%" if current_data['uk_inflation'] else "N/A",
            format_percentage(calculate_change(current_data, previous_data, 'uk_inflation')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'uk_inflation'))
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # US Rates
    with us_col:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.markdown("### US Rates")

        # US Base Rate
        st.metric(
            "Federal Funds Rate",
            f"{current_data['us_base_rate']:.2f}%" if current_data['us_base_rate'] else "N/A",
            format_percentage(calculate_change(current_data, previous_data, 'us_base_rate')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'us_base_rate'))
        )

        # US Inflation
        st.metric(
            "Inflation Rate",
            f"{current_data['us_inflation']:.2f}%" if current_data['us_inflation'] else "N/A",
            format_percentage(calculate_change(current_data, previous_data, 'us_inflation')),
            delta_color=get_delta_color(calculate_change(current_data, previous_data, 'us_inflation'))
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