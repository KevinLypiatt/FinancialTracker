import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from market_data import MarketDataFetcher
from supabase import create_client, Client
from typing import Optional
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

def init_supabase() -> Optional[Client]:
    """Initialize Supabase client with proper error handling"""
    try:
        logger.info("Attempting to connect to Supabase...")
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            logger.error("Supabase credentials not found in environment")
            return None

        client = create_client(supabase_url, supabase_key)
        logger.info("Successfully initialized Supabase client")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        return None

def collect_daily_data():
    """Collect and store daily market data in Supabase"""
    try:
        # Initialize Supabase client
        supabase = init_supabase()
        if not supabase:
            logger.error("Failed to initialize Supabase client")
            return False

        # Initialize market data fetcher
        market_fetcher = MarketDataFetcher()

        # Get market data
        logger.info("Fetching market data...")
        market_data = market_fetcher.get_market_data()

        if market_data:
            # Store data in Supabase
            logger.info("Attempting to store market data in Supabase...")
            result = supabase.table('financial_data').insert(market_data).execute()
            logger.info("Successfully stored daily market data")
            return True

        logger.error("No market data available to store")
        return False
    except Exception as e:
        logger.error(f"Error collecting daily data: {str(e)}")
        return False

if __name__ == "__main__":
    collect_daily_data()