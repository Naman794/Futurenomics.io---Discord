import discord
from discord import app_commands
from discord.ext import commands

from database.db import log_command
from services.intel_service import intel_service
from utils.embed_builder import build_error_embed, build_success_embed
from utils.formatters import truncate_text


class IntelCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ask", description="Ask Futurenomics crypto intel a question.")
    async def ask(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        item = intel_service.best_match(query)
        if not item:
            log_command(str(interaction.user.id), str(interaction.guild_id), "ask", query, "not_found")
            await interaction.followup.send(
                embed=build_error_embed(
                    "No Intel Found",
                    "I could not match that with the Futurenomics knowledge base yet. Try terms like `ETF outflows`, `oil BTC`, `stablecoins`, `liquidations`, or `Hyperliquid`.",
                ),
                ephemeral=True,
            )
            return

        title, description = intel_service.format_answer(item)
        log_command(str(interaction.user.id), str(interaction.guild_id), "ask", query, "success")
        await interaction.followup.send(embed=build_success_embed(title, truncate_text(description, 4000)))

    @app_commands.command(name="context", description="Get simple market context for a crypto narrative.")
    async def context(self, interaction: discord.Interaction, topic: str) -> None:
        await interaction.response.defer()
        item = intel_service.context_match(topic)
        if not item:
            log_command(str(interaction.user.id), str(interaction.guild_id), "context", topic, "not_found")
            await interaction.followup.send(
                embed=build_error_embed(
                    "No Context Found",
                    "Try a broader topic like `oil`, `ETF outflows`, `liquidations`, `stablecoins`, `DeFi`, or `crypto infrastructure`.",
                ),
                ephemeral=True,
            )
            return

        title, description = intel_service.format_answer(item)
        log_command(str(interaction.user.id), str(interaction.guild_id), "context", topic, "success")
        await interaction.followup.send(embed=build_success_embed(title, truncate_text(description, 4000)))

    @app_commands.command(name="related", description="Find related Futurenomics intel topics.")
    async def related(self, interaction: discord.Interaction, topic: str) -> None:
        await interaction.response.defer()
        items = intel_service.related(topic, limit=5)
        title, description = intel_service.format_related(items)
        status = "success" if items else "not_found"
        log_command(str(interaction.user.id), str(interaction.guild_id), "related", topic, status)
        await interaction.followup.send(embed=build_success_embed(title, truncate_text(description, 4000)))

    @app_commands.command(name="intel_list", description="List Futurenomics intel topics available in the bot.")
    async def intel_list(self, interaction: discord.Interaction) -> None:
        topics = intel_service.list_topics(limit=20)
        text = "\n".join(topics) if topics else "No intel topics loaded yet."
        log_command(str(interaction.user.id), str(interaction.guild_id), "intel_list", "", "success")
        await interaction.response.send_message(embed=build_success_embed("Futurenomics Intel Topics", truncate_text(text, 4000)), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(IntelCommands(bot))
