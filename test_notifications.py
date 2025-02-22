import os
import logging
from datetime import datetime, timezone
from notification_manager import NotificationManager
from market_data import MarketDataFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_notifications():
    try:
        logger.info("Starting notification test...")
        
        # Initialize notification manager and market data fetcher
        notification_manager = NotificationManager()
        market_fetcher = MarketDataFetcher()
        
        # Get current market data
        current_data = market_fetcher.get_market_data()
        
        # Create test data with significant changes to trigger alerts
        previous_data = current_data.copy()
        previous_data['gold_usd'] = current_data['gold_usd'] * 0.95  # 5% change
        
        # Test alert notifications
        logger.info("Testing market change alerts...")
        notification_manager.check_and_notify(current_data, previous_data)
        
        # Force a daily summary
        logger.info("Testing daily summary...")
        notification_manager.send_daily_summary(current_data)
        
        logger.info("Notification test completed")
        return True
        
    except Exception as e:
        logger.error(f"Error testing notifications: {str(e)}")
        return False

if __name__ == "__main__":
    test_notifications()
