import discord
from discord import app_commands
from discord.ext import commands

from cogs.intel_commands import IntelCommands
from database.db import log_command
from services.user_service import get_or_create_user
from utils.embed_builder import build_success_embed


class GeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="start", description="Create your learner profile.")
    async def start(self, interaction: discord.Interaction) -> None:
        user = get_or_create_user(str(interaction.user.id), interaction.user.name)
        log_command(str(interaction.user.id), str(interaction.guild_id), "start", "", "success")
        await interaction.response.send_message(embed=build_success_embed("Welcome to Web3 Teacher Bot", f"Profile ready for {user.get('username', interaction.user.name)}. Try /help, /learn bitcoin, or /ask ETF outflows."))

    @app_commands.command(name="help", description="Show available commands.")
    async def help(self, interaction: discord.Interaction) -> None:
        text = (
            "`/learn topic` `/glossary term` `/roadmap` `/quiz level`\n"
            "`/ask query` `/context topic` `/related topic` `/intel_list`\n"
            "`/price symbol` `/market symbol` `/top_gainers` `/top_losers` `/compare symbol1 symbol2`\n"
            "`/chart symbol interval` `/news query`\n"
            "`/alert symbol condition price` `/myalerts` `/delete_alert alert_id`\n"
            "`/subscribe_newsletter` `/set_newsletter_channel` `/send_newsletter_now`"
        )
        log_command(str(interaction.user.id), str(interaction.guild_id), "help", "", "success")
        await interaction.response.send_message(embed=build_success_embed("Help", text))

    @app_commands.command(name="about", description="About this bot.")
    async def about(self, interaction: discord.Interaction) -> None:
        log_command(str(interaction.user.id), str(interaction.guild_id), "about", "", "success")
        await interaction.response.send_message("I teach Web3 basics, show market data, chart Binance pairs, fetch crypto news, answer Futurenomics crypto-intel questions, and send daily educational newsletters.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GeneralCommands(bot))
    await bot.add_cog(IntelCommands(bot))
