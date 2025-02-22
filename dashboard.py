import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import time
from utils import get_delta_color, format_percentage
from market_data import MarketDataFetcher
import plotly.graph_objects as go
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
import os
import logging
import pathlib
import sys
import traceback
from notification_manager import NotificationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dashboard.log')
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection with proper error handling"""
    try:
        logger.info("Attempting to connect to database...")
        database_url = os.environ.get('DATABASE_URL')

        if not database_url:
            error_msg = "Database URL not found in environment"
            logger.error(error_msg)
            st.error("Database connection failed: Missing credentials")
            return None

        conn = psycopg2.connect(database_url)
        logger.info("Successfully connected to database")
        return conn
    except Exception as e:
        error_msg = f"Failed to connect to database: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        st.error(f"Database connection failed: {str(e)}")
        return None

def get_historical_data():
    """Fetch the last two days of data from database"""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Cannot fetch historical data: Database connection failed")
            return None

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM financial_data 
            ORDER BY timestamp DESC 
            LIMIT 2;
        """)
        results = cur.fetchall()

        if results:
            logger.info(f"Successfully fetched {len(results)} records")
            return pd.DataFrame(results)
        logger.warning("No historical data found")
        return None
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        st.error(f"Failed to fetch market data: {str(e)}")
        return None
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

try:
    logger.info("Starting dashboard initialization...")

    # Initialize NotificationManager
    notification_manager = NotificationManager()
    logger.info("NotificationManager initialized")


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
        try:
            logger.info("Starting main dashboard function")
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

        except Exception as e:
            logger.error(f"Error in main function: {str(e)}")
            logger.error(traceback.format_exc())
            st.error(f"Dashboard error: {str(e)}")

    if __name__ == "__main__":
        main()

except Exception as e:
    error_msg = f"Critical error during initialization: {str(e)}"
    logger.error(error_msg)
    logger.error(traceback.format_exc())
    st.error(f"Application failed to start: {str(e)}")
    sys.exit(1)