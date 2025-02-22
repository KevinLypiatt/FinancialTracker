import os
from datetime import datetime, timezone
from market_data import MarketDataFetcher
from typing import Optional
import logging
import sys
import traceback
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('daily_collector.log')
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Initialize database connection with proper error handling"""
    try:
        logger.info("Attempting to connect to database...")
        database_url = os.environ.get('DATABASE_URL')

        if not database_url:
            logger.error("Database URL not found in environment")
            return None

        conn = psycopg2.connect(database_url)
        logger.info("Successfully connected to database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        logger.error(f"Full error details: {traceback.format_exc()}")
        return None

def collect_daily_data():
    """Collect and store daily market data in database"""
    conn = None
    try:
        # Initialize database connection
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to initialize database connection")
            return False

        # Initialize market data fetcher
        market_fetcher = MarketDataFetcher()

        # Get market data
        logger.info("Fetching market data...")
        market_data = market_fetcher.get_market_data()

        if market_data:
            # Store data in database
            logger.info(f"Attempting to store market data: {market_data}")

            cur = conn.cursor()
            cur.execute("""
                INSERT INTO financial_data (
                    timestamp, gold_usd, gold_gbp, gbp_usd, sp500, bitcoin,
                    us_2y_yield, us_5y_yield, us_10y_yield, us_30y_yield,
                    uk_base_rate, uk_inflation, us_base_rate, us_inflation
                ) VALUES (
                    %(timestamp)s, %(gold_usd)s, %(gold_gbp)s, %(gbp_usd)s, 
                    %(sp500)s, %(bitcoin)s, %(us_2y_yield)s, %(us_5y_yield)s,
                    %(us_10y_yield)s, %(us_30y_yield)s, %(uk_base_rate)s,
                    %(uk_inflation)s, %(us_base_rate)s, %(us_inflation)s
                )
            """, market_data)

            conn.commit()
            cur.close()
            logger.info("Successfully stored daily market data")
            return True

        logger.error("No market data available to store")
        return False
    except Exception as e:
        logger.error(f"Error collecting daily data: {str(e)}")
        logger.error(f"Full error details: {traceback.format_exc()}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Starting daily data collection process...")
    success = collect_daily_data()
    logger.info(f"Daily data collection completed. Success: {success}")