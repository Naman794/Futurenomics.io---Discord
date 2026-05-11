import logging

import discord
from discord.ext import tasks

from config import DISCLAIMER
from services.binance_service import binance_service
from services.chart_service import create_candlestick_chart
from services.market_pulse_service import market_pulse_service

logger = logging.getLogger(__name__)

MAX_CHART_SYMBOLS_PER_CYCLE = 3


def setup_market_pulse_task(bot):
    @tasks.loop(minutes=1)
    async def market_pulse():
        settings_rows = market_pulse_service.get_active_settings()
        for settings in settings_rows:
            await _process_guild_market_pulse(bot, settings)

    return market_pulse


async def _process_guild_market_pulse(bot, settings: dict, force: bool = False) -> None:
    guild_id = str(settings["discord_guild_id"])
    channel_id = settings.get("channel_id")
    symbols = settings.get("symbols") or ""
    update_interval = int(settings.get("update_interval_minutes") or 1)
    chart_interval = int(settings.get("chart_interval_minutes") or 5)

    if not channel_id:
        market_pulse_service.log_pulse(guild_id, channel_id, symbols, "failed", "No market pulse channel configured")
        return

    if not force and not market_pulse_service.should_send_update(guild_id, update_interval):
        return

    try:
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            channel = await bot.fetch_channel(int(channel_id))
    except Exception as exc:
        logger.exception("Market pulse channel fetch failed for guild %s", guild_id)
        market_pulse_service.log_pulse(guild_id, channel_id, symbols, "failed", f"Channel fetch failed: {exc}")
        return

    if channel is None:
        market_pulse_service.log_pulse(guild_id, channel_id, symbols, "failed", "Channel not found")
        return

    try:
        embed = await market_pulse_service.build_market_pulse_embed(symbols)
        # TODO: Store latest market pulse message ID and edit it instead of always sending a new message.
        await channel.send(embed=embed)
        market_pulse_service.log_pulse(guild_id, channel_id, symbols, "sent")
    except Exception as exc:
        logger.exception("Market pulse send failed for guild %s", guild_id)
        market_pulse_service.log_pulse(guild_id, channel_id, symbols, "failed", f"Embed send failed: {exc}")
        return

    if not market_pulse_service.should_send_chart(guild_id, chart_interval):
        return

    chart_errors: list[str] = []
    chart_files: list[discord.File] = []
    for symbol in market_pulse_service.normalize_symbols(symbols)[:MAX_CHART_SYMBOLS_PER_CYCLE]:
        try:
            klines = await binance_service.get_klines(symbol, "1h", 100)
            chart_path = create_candlestick_chart(symbol, klines)
            chart_files.append(discord.File(chart_path))
        except Exception as exc:
            logger.exception("Chart generation failed for %s in guild %s", symbol, guild_id)
            chart_errors.append(f"{symbol}: {exc}")

    if not chart_files:
        if chart_errors:
            market_pulse_service.log_pulse(guild_id, channel_id, symbols, "partial", "; ".join(chart_errors))
        return

    try:
        await channel.send(
            content=f"Market pulse charts. {DISCLAIMER}",
            files=chart_files,
        )
        error_message = "; ".join(chart_errors) if chart_errors else None
        market_pulse_service.log_pulse(guild_id, channel_id, symbols, "chart_sent", error_message)
    except Exception as exc:
        logger.exception("Market pulse chart send failed for guild %s", guild_id)
        market_pulse_service.log_pulse(guild_id, channel_id, symbols, "partial", f"Chart send failed: {exc}")
