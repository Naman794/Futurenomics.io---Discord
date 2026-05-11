from discord.ext import tasks

from database.db import execute_query
from services.binance_service import binance_service


def setup_market_snapshot_task():
    @tasks.loop(minutes=15)
    async def market_snapshot():
        for symbol in ("BTCUSDT", "ETHUSDT"):
            data = await binance_service.get_24h_ticker(symbol)
            execute_query(
                """
                INSERT INTO market_snapshots(symbol, price, price_change_percent, volume, high_24h, low_24h)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (data["symbol"], data["price"], data["price_change_percent"], data["volume"], data["high_24h"], data["low_24h"]),
            )

    return market_snapshot
