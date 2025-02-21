import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from market_data import MarketDataFetcher
from supabase import create_client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def collect_daily_data():
    """Collect and store daily market data in Supabase"""
    try:
        # Initialize Supabase client
        supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
        
        # Initialize market data fetcher
        market_fetcher = MarketDataFetcher()
        
        # Get market data
        market_data = market_fetcher.get_market_data()
        
        if market_data:
            # Store data in Supabase
            supabase.table('financial_data').insert(market_data).execute()
            logger.info("Successfully stored daily market data")
            return True
    except Exception as e:
        logger.error(f"Error collecting daily data: {str(e)}")
        return False

if __name__ == "__main__":
    collect_daily_data()
