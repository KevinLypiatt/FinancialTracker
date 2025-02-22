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
        """Get UK base rate and inflation rate"""
        try:
            # Using UK 2Y Gilt yield as a proxy for base rate
            uk_base = self.get_stock_data("^TMBMKGB-02Y")
            # Using RPI as proxy for inflation
            uk_inflation = self.get_stock_data("^UKRPI")

            return {
                "uk_base_rate": uk_base,
                "uk_inflation": uk_inflation
            }
        except Exception as e:
            self.logger.error(f"Error fetching UK rates: {str(e)}")
            return {"uk_base_rate": None, "uk_inflation": None}

    def get_us_rates(self) -> Dict[str, Optional[float]]:
        """Get US federal funds rate and inflation rate"""
        try:
            # Using US 2Y Treasury yield as proxy for Fed rate
            us_base = self.get_stock_data("^IRX")
            # Using Core CPI as proxy for inflation
            us_inflation = self.get_stock_data("^CPI")

            return {
                "us_base_rate": us_base,
                "us_inflation": us_inflation
            }
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

            data.update(self.get_us_yield_curve())
            data.update(self.get_uk_rates())
            data.update(self.get_us_rates())

            if data["gold_usd"] and data["gbp_usd"]:
                data["gold_gbp"] = data["gold_usd"] / data["gbp_usd"]
            else:
                data["gold_gbp"] = None

            return data
        except Exception as e:
            self.logger.error(f"Error fetching market data: {str(e)}")
            raise