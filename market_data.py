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

    def get_market_data(self) -> Dict[str, Any]:
        try:
            gold_usd = self.get_stock_data("GC=F")
            gbp_usd = self.get_forex_rate()
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "gold_usd": gold_usd,
                "gold_gbp": gold_usd / gbp_usd if gold_usd and gbp_usd else None,
                "gbp_usd": gbp_usd,
                "sp500": self.get_stock_data("^GSPC"),
                "bitcoin": self.get_stock_data("BTC-USD"),
                **self.get_us_yield_curve()
            }
        except Exception as e:
            self.logger.error(f"Error fetching market data: {str(e)}")
            raise
