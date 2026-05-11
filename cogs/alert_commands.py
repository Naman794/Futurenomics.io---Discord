import discord
from discord import app_commands
from discord.ext import commands

from config import DISCLAIMER
from services.alert_service import create_alert, delete_alert, get_user_alerts
from utils.embed_builder import build_error_embed, build_success_embed
from utils.formatters import format_price
from utils.validators import validate_alert_condition, validate_price


class AlertCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="alert", description="Create a price alert.")
    async def alert(self, interaction: discord.Interaction, symbol: str, condition: str, price: float) -> None:
        if not validate_alert_condition(condition) or not validate_price(price):
            await interaction.response.send_message(embed=build_error_embed("Invalid alert", "Use: /alert BTCUSDT above 70000 or /alert ETHUSDT below 3000"), ephemeral=True)
            return
        alert_id = create_alert(str(interaction.user.id), symbol, condition, price)
        await interaction.response.send_message(embed=build_success_embed("Alert created", f"Alert #{alert_id}: {symbol.upper()} {condition.lower()} {format_price(price)}\n{DISCLAIMER}"), ephemeral=True)

    @app_commands.command(name="myalerts", description="Show your active alerts.")
    async def myalerts(self, interaction: discord.Interaction) -> None:
        alerts = get_user_alerts(str(interaction.user.id))
        text = "\n".join(f"#{a['id']} {a['symbol']} {a['condition_type']} {format_price(a['target_price'])}" for a in alerts) or "No active alerts."
        await interaction.response.send_message(embed=build_success_embed("My Alerts", text), ephemeral=True)

    @app_commands.command(name="delete_alert", description="Delete one of your alerts.")
    async def delete_alert_cmd(self, interaction: discord.Interaction, alert_id: int) -> None:
        delete_alert(alert_id, str(interaction.user.id))
        await interaction.response.send_message(embed=build_success_embed("Alert deleted", f"Alert #{alert_id} disabled."), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AlertCommands(bot))
