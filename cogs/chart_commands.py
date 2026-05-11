import discord
from discord import app_commands
from discord.ext import commands

from config import DISCLAIMER
from services.binance_service import binance_service
from services.chart_service import create_candlestick_chart
from utils.embed_builder import build_error_embed
from utils.validators import validate_interval


class ChartCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="chart", description="Generate a candlestick chart.")
    async def chart(self, interaction: discord.Interaction, symbol: str, interval: str = "1h") -> None:
        await interaction.response.defer()
        if not validate_interval(interval):
            await interaction.followup.send(embed=build_error_embed("Invalid interval", "Supported: 1m, 5m, 15m, 1h, 4h, 1d"), ephemeral=True)
            return
        try:
            normalized = binance_service.normalize_symbol(symbol)
            klines = await binance_service.get_klines(normalized, interval, 100)
            path = create_candlestick_chart(normalized, klines)
            await interaction.followup.send(content=DISCLAIMER, file=discord.File(path))
        except Exception as exc:
            await interaction.followup.send(embed=build_error_embed("Chart failed", str(exc)), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChartCommands(bot))
