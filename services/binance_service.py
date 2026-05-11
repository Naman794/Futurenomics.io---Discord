import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com/api/v3"


class BinanceService:
    def __init__(self, timeout: int = 10) -> None:
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    def normalize_symbol(self, symbol: str) -> str:
        cleaned = symbol.strip().upper().replace("-", "").replace("/", "")
        if cleaned and not cleaned.endswith("USDT") and len(cleaned) <= 6:
            cleaned = f"{cleaned}USDT"
        return cleaned

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict | list:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{BASE_URL}{path}", params=params) as response:
                    if response.status == 429:
                        raise RuntimeError("Binance rate limit reached. Please try again later.")
                    if response.status >= 500:
                        raise RuntimeError("Binance API is temporarily unavailable.")
                    data = await response.json()
                    if response.status >= 400:
                        message = data.get("msg", "Invalid Binance request") if isinstance(data, dict) else "Invalid Binance request"
                        raise ValueError(message)
                    return data
        except TimeoutError as exc:
            raise RuntimeError("Binance request timed out.") from exc
        except aiohttp.ClientError as exc:
            logger.warning("Binance client error: %s", exc)
            raise RuntimeError("Could not reach Binance API.") from exc

    async def validate_symbol(self, symbol: str) -> bool:
        try:
            await self.get_price(symbol)
            return True
        except Exception:
            return False

    async def get_price(self, symbol: str) -> dict:
        normalized = self.normalize_symbol(symbol)
        data = await self._get("/ticker/price", {"symbol": normalized})
        return {"symbol": normalized, "price": float(data["price"])}

    async def get_24h_ticker(self, symbol: str) -> dict:
        normalized = self.normalize_symbol(symbol)
        data = await self._get("/ticker/24hr", {"symbol": normalized})
        return {
            "symbol": normalized,
            "price": float(data["lastPrice"]),
            "price_change_percent": float(data["priceChangePercent"]),
            "volume": float(data["volume"]),
            "high_24h": float(data["highPrice"]),
            "low_24h": float(data["lowPrice"]),
        }

    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> list[dict]:
        normalized = self.normalize_symbol(symbol)
        data = await self._get("/klines", {"symbol": normalized, "interval": interval, "limit": limit})
        return [
            {
                "open_time": int(item[0]),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
                "close_time": int(item[6]),
            }
            for item in data
        ]

    async def _top_movers(self, reverse: bool, limit: int) -> list[dict]:
        data = await self._get("/ticker/24hr")
        usdt_pairs = [item for item in data if item.get("symbol", "").endswith("USDT")]
        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x.get("priceChangePercent", 0)), reverse=reverse)
        return [
            {
                "symbol": item["symbol"],
                "price": float(item["lastPrice"]),
                "price_change_percent": float(item["priceChangePercent"]),
                "volume": float(item["volume"]),
            }
            for item in sorted_pairs[:limit]
        ]

    async def get_top_gainers(self, limit: int = 10) -> list[dict]:
        return await self._top_movers(True, limit)

    async def get_top_losers(self, limit: int = 10) -> list[dict]:
        return await self._top_movers(False, limit)


binance_service = BinanceService()
