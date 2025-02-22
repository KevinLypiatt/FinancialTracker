import logging
from typing import Dict, Any, Optional
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
        """Get UK base rate and inflation rate using FRED API"""
        try:
            # Get Bank of England Official Bank Rate from FRED
            # Using a longer timeframe to ensure we have data
            uk_base = self.fred.get_series('IUDSOIA', 
                                       observation_start=datetime.now() - timedelta(days=60))
            if uk_base.empty:
                raise ValueError("No UK base rate data available")
            latest_rate = float(uk_base.iloc[-1])

            # Get UK CPI data for inflation calculation
            uk_cpi = self.fred.get_series('GBRCPIALLMINMEI', 
                                      observation_start=datetime.now() - timedelta(days=400))
            if uk_cpi.empty:
                raise ValueError("No UK CPI data available")
            latest_cpi = float(uk_cpi.iloc[-1])
            # Get year-ago value, handle case where we might not have exactly 13 months
            year_ago_index = -13 if len(uk_cpi) >= 13 else 0
            year_ago_cpi = float(uk_cpi.iloc[year_ago_index])
            inflation_rate = ((latest_cpi - year_ago_cpi) / year_ago_cpi) * 100

            rates = {
                "uk_base_rate": latest_rate,
                "uk_inflation": inflation_rate
            }
            self.logger.info(f"UK rates from FRED: {rates}")
            return rates
        except Exception as e:
            self.logger.error(f"Error fetching UK rates: {str(e)}")
            # Fallback to Yahoo Finance data
            try:
                uk_base = self.get_stock_data("^GB2YR")  # UK 2Y Gilt yield as proxy
                uk_gilt = self.get_stock_data("^GB10YR")  # UK 10Y Gilt yield

                rates = {
                    "uk_base_rate": uk_base,
                    "uk_inflation": uk_gilt
                }
                self.logger.info(f"UK rates from Yahoo Finance (fallback): {rates}")
                return rates
            except Exception as fallback_error:
                self.logger.error(f"Error fetching UK rates fallback: {str(fallback_error)}")
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