from datetime import datetime, timedelta
import logging

import discord

from config import DISCLAIMER
from database.db import execute_query, fetch_all, fetch_one
from services.binance_service import binance_service
from utils.formatters import format_percent, format_price, format_volume

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT"


class MarketPulseService:
    def get_or_create_settings(self, guild_id: str) -> dict:
        settings = fetch_one(
            "SELECT * FROM market_pulse_settings WHERE discord_guild_id = ?",
            (guild_id,),
        )
        if settings:
            return settings

        execute_query(
            "INSERT INTO market_pulse_settings(discord_guild_id) VALUES (?)",
            (guild_id,),
        )
        return fetch_one(
            "SELECT * FROM market_pulse_settings WHERE discord_guild_id = ?",
            (guild_id,),
        ) or {}

    def set_channel(self, guild_id: str, channel_id: str) -> dict:
        self.get_or_create_settings(guild_id)
        execute_query(
            """
            UPDATE market_pulse_settings
            SET channel_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_guild_id = ?
            """,
            (channel_id, guild_id),
        )
        return self.get_or_create_settings(guild_id)

    def set_symbols(self, guild_id: str, symbols: str) -> dict:
        normalized = self.normalize_symbols(symbols)
        self.get_or_create_settings(guild_id)
        execute_query(
            """
            UPDATE market_pulse_settings
            SET symbols = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_guild_id = ?
            """,
            (",".join(normalized), guild_id),
        )
        return self.get_or_create_settings(guild_id)

    def set_update_interval(self, guild_id: str, minutes: int) -> dict:
        minutes = max(1, int(minutes))
        self.get_or_create_settings(guild_id)
        execute_query(
            """
            UPDATE market_pulse_settings
            SET update_interval_minutes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_guild_id = ?
            """,
            (minutes, guild_id),
        )
        return self.get_or_create_settings(guild_id)

    def set_chart_interval(self, guild_id: str, minutes: int) -> dict:
        minutes = max(5, int(minutes))
        self.get_or_create_settings(guild_id)
        execute_query(
            """
            UPDATE market_pulse_settings
            SET chart_interval_minutes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE discord_guild_id = ?
            """,
            (minutes, guild_id),
        )
        return self.get_or_create_settings(guild_id)

    def start(self, guild_id: str) -> dict:
        self.get_or_create_settings(guild_id)
        execute_query(
            """
            UPDATE market_pulse_settings
            SET is_active = 1, updated_at = CURRENT_TIMESTAMP
            WHERE discord_guild_id = ?
            """,
            (guild_id,),
        )
        return self.get_or_create_settings(guild_id)

    def stop(self, guild_id: str) -> dict:
        self.get_or_create_settings(guild_id)
        execute_query(
            """
            UPDATE market_pulse_settings
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE discord_guild_id = ?
            """,
            (guild_id,),
        )
        return self.get_or_create_settings(guild_id)

    def get_active_settings(self) -> list[dict]:
        return fetch_all(
            """
            SELECT * FROM market_pulse_settings
            WHERE is_active = 1 AND channel_id IS NOT NULL
            """
        )

    async def build_market_pulse_embed(self, symbols: str | list[str]) -> discord.Embed:
        symbol_list = self.normalize_symbols(symbols)
        embed = discord.Embed(
            title="Futurenomics Live Market Pulse",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )

        for symbol in symbol_list:
            try:
                ticker = await binance_service.get_24h_ticker(symbol)
                change = ticker["price_change_percent"]
                status = self._change_status(change)
                value = (
                    f"{status} Price: {format_price(ticker['price'])}\n"
                    f"24h Change: {format_percent(change)}\n"
                    f"24h High: {format_price(ticker['high_24h'])}\n"
                    f"24h Low: {format_price(ticker['low_24h'])}\n"
                    f"Volume: {format_volume(ticker['volume'])}"
                )
                embed.add_field(name=ticker["symbol"], value=value, inline=False)
            except Exception as exc:
                logger.exception("Failed to build pulse row for %s", symbol)
                embed.add_field(
                    name=symbol,
                    value=f"Data unavailable right now: {exc}",
                    inline=False,
                )

        embed.set_footer(text=DISCLAIMER)
        return embed

    def should_send_update(self, guild_id: str, update_interval_minutes: int) -> bool:
        return self._enough_time_since_status(
            guild_id=guild_id,
            interval_minutes=max(1, int(update_interval_minutes)),
            statuses=("sent", "partial", "chart_sent"),
        )

    def should_send_chart(self, guild_id: str, chart_interval_minutes: int) -> bool:
        return self._enough_time_since_status(
            guild_id=guild_id,
            interval_minutes=max(5, int(chart_interval_minutes)),
            statuses=("chart_sent",),
        )

    def log_pulse(
        self,
        guild_id: str,
        channel_id: str | None,
        symbols: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        execute_query(
            """
            INSERT INTO market_pulse_logs(discord_guild_id, channel_id, symbols, status, error_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, channel_id, symbols, status, error_message),
        )

    def normalize_symbols(self, symbols: str | list[str]) -> list[str]:
        if isinstance(symbols, str):
            raw_symbols = symbols.split(",")
        else:
            raw_symbols = symbols

        normalized: list[str] = []
        for symbol in raw_symbols:
            cleaned = binance_service.normalize_symbol(str(symbol))
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized or DEFAULT_SYMBOLS.split(",")

    def _enough_time_since_status(self, guild_id: str, interval_minutes: int, statuses: tuple[str, ...]) -> bool:
        placeholders = ",".join("?" for _ in statuses)
        row = fetch_one(
            f"""
            SELECT sent_at FROM market_pulse_logs
            WHERE discord_guild_id = ? AND status IN ({placeholders})
            ORDER BY sent_at DESC
            LIMIT 1
            """,
            (guild_id, *statuses),
        )
        if not row:
            return True

        last_sent = self._parse_db_timestamp(row["sent_at"])
        if last_sent is None:
            return True
        return datetime.utcnow() - last_sent >= timedelta(minutes=interval_minutes)

    @staticmethod
    def _parse_db_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value.split("+")[0], fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _change_status(change: float) -> str:
        if change > 0:
            return "🟢"
        if change < 0:
            return "🔴"
        return "⚪"


market_pulse_service = MarketPulseService()
