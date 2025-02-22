import logging
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import datetime, timezone, timedelta
import time
from threading import Lock
from dataclasses import dataclass
from fredapi import Fred
import os

@dataclass
class RateLimiter:
    calls_per_second: int
    _last_call_time: float = 0.0
    _lock: Lock = Lock()

    def wait(self):
        with self._lock:
            current_time = time.time()
            time_since_last_call = current_time - self._last_call_time
            if time_since_last_call < 1.0 / self.calls_per_second:
                time.sleep(1.0 / self.calls_per_second - time_since_last_call)
            self._last_call_time = time.time()

class MarketDataFetcher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rate_limiter = RateLimiter(calls_per_second=2)
        # Initialize FRED API client
        self.fred = Fred(api_key=os.environ.get('FRED_API_KEY'))

    def get_forex_rate(self, symbol: str = "GBPUSD=X") -> Optional[float]:
        return self.get_stock_data(symbol)

    def get_us_yield_curve(self) -> Dict[str, Optional[float]]:
        yields = {
            "us_2y_yield": self.get_stock_data("^IRX"),
            "us_5y_yield": self.get_stock_data("^FVX"),
            "us_10y_yield": self.get_stock_data("^TNX"),
            "us_30y_yield": self.get_stock_data("^TYX")
        }
        return yields

    def get_stock_data(self, symbol: str, period: str = "1d") -> Optional[float]:
        try:
            self.rate_limiter.wait()
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            return float(data["Close"].iloc[-1]) if not data.empty else None
        except Exception as e:
            self.logger.error(f"Error fetching stock data for {symbol}: {str(e)}")
            return None

    def get_trading_economics_data(self, country: str, indicator: str) -> Optional[float]:
        """This method is deprecated and will be removed"""
        self.logger.warning("Trading Economics API is no longer used")
        return None

    def get_uk_rates(self) -> Dict[str, Optional[float]]:
        """Get UK base rate from Bank of England and inflation rate"""
        try:
            # Fetch Bank of England base rate
            url = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            cookies = {
                'cookie_consent': 'accepted',
                'cookie_consent_essential': 'accepted'
            }
            
            session = requests.Session()
            response = session.get(url, headers=headers, cookies=cookies)
            
            uk_base = None
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table')
                if table:
                    latest_row = table.find_all('tr')[1]
                    rate = latest_row.find_all('td')[1].text.strip()
                    uk_base = float(rate.replace('%', ''))

            # Use Gilt yield as inflation indicator
            uk_gilt = self.get_stock_data("^GB10YR")

            rates = {
                "uk_base_rate": uk_base,
                "uk_inflation": uk_gilt
            }
            self.logger.info(f"UK rates: {rates}")
            return rates
        except Exception as e:
            self.logger.error(f"Error fetching UK rates: {str(e)}")
            return {"uk_base_rate": None, "uk_inflation": None}

    def get_us_rates(self) -> Dict[str, Optional[float]]:
        """Get US federal funds rate and inflation rate using FRED API"""
        try:
            # Get latest Federal Funds Rate
            fed_rate = self.fred.get_series('FEDFUNDS', 
                                          observation_start=datetime.now() - timedelta(days=30))
            latest_rate = float(fed_rate.iloc[-1])

            # Get CPI data for last 13 months to calculate YoY inflation
            cpi = self.fred.get_series('CPIAUCSL', 
                                     observation_start=datetime.now() - timedelta(days=400))
            latest_cpi = float(cpi.iloc[-1])
            year_ago_cpi = float(cpi.iloc[-13])  # 13 months ago
            inflation_rate = ((latest_cpi - year_ago_cpi) / year_ago_cpi) * 100

            rates = {
                "us_base_rate": latest_rate,
                "us_inflation": inflation_rate
            }
            self.logger.info(f"US rates from FRED: {rates}")
            return rates
        except Exception as e:
            self.logger.error(f"Error fetching US rates from FRED: {str(e)}")
            # Fallback to Yahoo Finance data if FRED fails
            try:
                us_base = self.get_stock_data("^IRX")  # US 13-week Treasury Bill rate
                us_tips = self.get_stock_data("^TNX")  # US 10Y Treasury yield as inflation indicator

                # Convert basis points to percentage only if us_base is not None
                if us_base is not None:
                    us_base = us_base / 100

                rates = {
                    "us_base_rate": us_base,
                    "us_inflation": us_tips
                }
                self.logger.info(f"US rates from Yahoo Finance (fallback): {rates}")
                return rates
            except Exception as fallback_error:
                self.logger.error(f"Error fetching US rates fallback: {str(fallback_error)}")
                return {"us_base_rate": None, "us_inflation": None}

    def get_market_data(self) -> Dict[str, Any]:
        try:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "gold_usd": self.get_stock_data("GC=F"),
                "gbp_usd": self.get_forex_rate(),
                "sp500": self.get_stock_data("^GSPC"),
                "bitcoin": self.get_stock_data("BTC-USD"),
            }

            # Get rates data
            uk_rates = self.get_uk_rates()
            us_rates = self.get_us_rates()

            # Update the data dictionary with all rates
            data.update(self.get_us_yield_curve())
            data.update(uk_rates)
            data.update(us_rates)

            # Calculate Gold in GBP
            if data["gold_usd"] and data["gbp_usd"]:
                data["gold_gbp"] = data["gold_usd"] / data["gbp_usd"]
            else:
                data["gold_gbp"] = None

            self.logger.info(f"Complete market data: {data}")
            return data
        except Exception as e:
            self.logger.error(f"Error fetching market data: {str(e)}")
            raise