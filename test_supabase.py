import os
import logging
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('supabase_test.log')
    ]
)
logger = logging.getLogger(__name__)

def test_database_connection():
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')

        logger.info("Attempting to connect to database...")
        logger.info(f"Database URL available: {'Yes' if database_url else 'No'}")

        # Connect to the database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Try a simple query
        cur.execute("SELECT * FROM financial_data LIMIT 1;")
        result = cur.fetchall()

        if result:
            logger.info("Successfully connected to database and retrieved data")
            logger.info(f"Retrieved {len(result)} records")
            return True
        else:
            logger.warning("Connected to database but no data found")
            return True

    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        logger.error("Full traceback:", exc_info=True)
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    test_database_connection()