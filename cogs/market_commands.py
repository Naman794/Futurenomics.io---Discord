import discord
from discord import app_commands
from discord.ext import commands

from config import DISCLAIMER
from database.db import log_command
from services.binance_service import binance_service
from utils.embed_builder import build_error_embed, build_market_embed, build_success_embed
from utils.formatters import format_percent, format_price
from utils.validators import validate_crypto_symbol


class MarketCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="price", description="Get the latest Binance price for a symbol.")
    async def price(self, interaction: discord.Interaction, symbol: str) -> None:
        await interaction.response.defer()
        if not validate_crypto_symbol(binance_service.normalize_symbol(symbol)):
            await interaction.followup.send(embed=build_error_embed("Invalid symbol", "Use a Binance-style symbol such as BTCUSDT or ETH."), ephemeral=True)
            return
        try:
            data = await binance_service.get_price(symbol)
            log_command(str(interaction.user.id), str(interaction.guild_id), "price", symbol, "success")
            await interaction.followup.send(embed=build_market_embed("Market Price", data))
        except Exception as exc:
            log_command(str(interaction.user.id), str(interaction.guild_id), "price", symbol, "error")
            await interaction.followup.send(embed=build_error_embed("Price unavailable", str(exc)), ephemeral=True)

    @app_commands.command(name="market", description="Get 24h market data for a symbol.")
    async def market(self, interaction: discord.Interaction, symbol: str) -> None:
        await interaction.response.defer()
        try:
            data = await binance_service.get_24h_ticker(symbol)
            await interaction.followup.send(embed=build_market_embed("24h Market Snapshot", data))
        except Exception as exc:
            await interaction.followup.send(embed=build_error_embed("Market unavailable", str(exc)), ephemeral=True)

    @app_commands.command(name="top_gainers", description="Show top USDT gainers.")
    async def top_gainers(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        rows = await binance_service.get_top_gainers(10)
        text = "\n".join(f"{x['symbol']}: {format_price(x['price'])} ({format_percent(x['price_change_percent'])})" for x in rows)
        await interaction.followup.send(embed=build_success_embed("Top Gainers", f"{text}\n\n{DISCLAIMER}"))

    @app_commands.command(name="top_losers", description="Show top USDT losers.")
    async def top_losers(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        rows = await binance_service.get_top_losers(10)
        text = "\n".join(f"{x['symbol']}: {format_price(x['price'])} ({format_percent(x['price_change_percent'])})" for x in rows)
        await interaction.followup.send(embed=build_success_embed("Top Losers", f"{text}\n\n{DISCLAIMER}"))

    @app_commands.command(name="compare", description="Compare two symbols.")
    async def compare(self, interaction: discord.Interaction, symbol1: str, symbol2: str) -> None:
        await interaction.response.defer()
        one = await binance_service.get_24h_ticker(symbol1)
        two = await binance_service.get_24h_ticker(symbol2)
        text = (
            f"{one['symbol']}: {format_price(one['price'])} ({format_percent(one['price_change_percent'])})\n"
            f"{two['symbol']}: {format_price(two['price'])} ({format_percent(two['price_change_percent'])})\n\n{DISCLAIMER}"
        )
        await interaction.followup.send(embed=build_success_embed("Comparison", text))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MarketCommands(bot))
