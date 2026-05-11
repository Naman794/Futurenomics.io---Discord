import logging

from config import DISCLAIMER
from database.db import execute_query
from services.binance_service import binance_service
from services.education_service import list_lessons
from services.news_service import fetch_latest_news, save_article, summarize_news
from utils.embed_builder import build_newsletter_embed
from utils.formatters import format_percent, format_price

logger = logging.getLogger(__name__)


async def build_daily_newsletter() -> tuple[str, str]:
    btc = await binance_service.get_24h_ticker("BTCUSDT")
    eth = await binance_service.get_24h_ticker("ETHUSDT")
    gainers = await binance_service.get_top_gainers(3)
    losers = await binance_service.get_top_losers(3)
    articles = fetch_latest_news(limit=5)
    for article in articles:
        save_article(article)
    concept = (list_lessons() or [{"title": "Wallet safety"}])[0]["title"]

    lines = [
        "Good day, Web3 learners.",
        "",
        f"BTC: {format_price(btc['price'])} ({format_percent(btc['price_change_percent'])} 24h)",
        f"ETH: {format_price(eth['price'])} ({format_percent(eth['price_change_percent'])} 24h)",
        "",
        "Top gainers: " + ", ".join(f"{x['symbol']} {format_percent(x['price_change_percent'])}" for x in gainers),
        "Top losers: " + ", ".join(f"{x['symbol']} {format_percent(x['price_change_percent'])}" for x in losers),
        "",
        "Headlines:",
        summarize_news(articles),
        "",
        f"Concept of the day: {concept}",
        "",
        DISCLAIMER,
    ]
    return "Daily Web3 Market Brief", "\n".join(lines)


async def send_newsletter(bot, guild_id: str, channel_id: str) -> bool:
    title, content = await build_daily_newsletter()
    channel = bot.get_channel(int(channel_id))
    if channel is None:
        try:
            channel = await bot.fetch_channel(int(channel_id))
        except Exception:
            logger.exception("Newsletter channel not found: %s", channel_id)
            save_newsletter_log(guild_id, channel_id, title, content, "failed")
            return False
    await channel.send(embed=build_newsletter_embed(title, content))
    save_newsletter_log(guild_id, channel_id, title, content, "sent")
    return True


def save_newsletter_log(guild_id: str, channel_id: str, title: str, content: str, status: str) -> None:
    execute_query(
        "INSERT INTO newsletters(guild_id, channel_id, title, content, status) VALUES (?, ?, ?, ?, ?)",
        (guild_id, channel_id, title, content, status),
    )
