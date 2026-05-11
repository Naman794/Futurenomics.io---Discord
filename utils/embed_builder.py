import discord

from config import DISCLAIMER
from utils.formatters import format_percent, format_price, format_volume, truncate_text


def build_success_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=discord.Color.green())


def build_error_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=discord.Color.red())


def build_market_embed(title: str, data: dict) -> discord.Embed:
    embed = discord.Embed(title=title, color=discord.Color.blue())
    embed.add_field(name="Symbol", value=data.get("symbol", "N/A"), inline=True)
    embed.add_field(name="Price", value=format_price(data.get("price")), inline=True)
    if "price_change_percent" in data:
        embed.add_field(name="24h Change", value=format_percent(data.get("price_change_percent")), inline=True)
    if "volume" in data:
        embed.add_field(name="Volume", value=format_volume(data.get("volume")), inline=True)
    if "high_24h" in data:
        embed.add_field(name="24h High", value=format_price(data.get("high_24h")), inline=True)
    if "low_24h" in data:
        embed.add_field(name="24h Low", value=format_price(data.get("low_24h")), inline=True)
    embed.set_footer(text=DISCLAIMER)
    return embed


def build_news_embed(articles: list[dict]) -> discord.Embed:
    embed = discord.Embed(title="Latest Web3 News", color=discord.Color.orange())
    if not articles:
        embed.description = "No articles found right now."
        embed.set_footer(text=DISCLAIMER)
        return embed
    for article in articles[:5]:
        title = truncate_text(article.get("title", "Untitled"), 80)
        value = article.get("url") or article.get("summary") or "No link available"
        embed.add_field(name=title, value=truncate_text(value, 180), inline=False)
    embed.set_footer(text=DISCLAIMER)
    return embed


def build_newsletter_embed(title: str, content: str) -> discord.Embed:
    embed = discord.Embed(title=title, description=truncate_text(content, 4096), color=discord.Color.gold())
    embed.set_footer(text=DISCLAIMER)
    return embed


def build_lesson_embed(title: str, content: str) -> discord.Embed:
    return discord.Embed(title=title, description=truncate_text(content, 4096), color=discord.Color.purple())
