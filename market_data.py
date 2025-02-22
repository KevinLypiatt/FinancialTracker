import logging
from typing import Dict, Any, Optional
import yfinance as yf
from datetime import datetime, timezone
import time
from threading import Lock
from dataclasses import dataclass

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

    def get_uk_rates(self) -> Dict[str, Optional[float]]:
        """Get UK base rate and inflation rate using fixed values"""
        try:
            # Using fixed values for UK rates
            rates = {
                "uk_base_rate": 4.5,  # Current Bank of England base rate
                "uk_inflation": 3.0   # Current UK CPI
            }
            self.logger.info(f"UK rates: {rates}")  # Add logging to debug
            return rates
        except Exception as e:
            self.logger.error(f"Error fetching UK rates: {str(e)}")
            return {"uk_base_rate": None, "uk_inflation": None}

    def get_us_rates(self) -> Dict[str, Optional[float]]:
        """Get US federal funds rate and inflation rate"""
        try:
            rates = {
                "us_base_rate": 4.375,  # Average of 4.25-4.5% range
                "us_inflation": 3.0     # Current US CPI
            }
            self.logger.info(f"US rates: {rates}")  # Add logging to debug
            return rates
        except Exception as e:
            self.logger.error(f"Error fetching US rates: {str(e)}")
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

            self.logger.info(f"Complete market data: {data}")  # Add logging to debug
            return data
        except Exception as e:
            self.logger.error(f"Error fetching market data: {str(e)}")
            raise