import discord
from discord import app_commands
from discord.ext import commands

from database.db import execute_query, fetch_one, log_command
from services.newsletter_service import send_newsletter
from utils.embed_builder import build_error_embed, build_success_embed


class NewsletterCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="set_newsletter_channel", description="Set this channel for daily newsletters.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_newsletter_channel(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=build_error_embed("Guild only", "Use this command inside a server."), ephemeral=True)
            return
        execute_query(
            """
            INSERT INTO guilds(discord_guild_id, guild_name, newsletter_channel_id)
            VALUES (?, ?, ?)
            ON CONFLICT(discord_guild_id) DO UPDATE SET guild_name = excluded.guild_name, newsletter_channel_id = excluded.newsletter_channel_id
            """,
            (str(interaction.guild.id), interaction.guild.name, str(interaction.channel_id)),
        )
        await interaction.response.send_message(embed=build_success_embed("Newsletter channel set", "Daily newsletters will be sent here."))

    @app_commands.command(name="subscribe_newsletter", description="Subscribe yourself to newsletter updates.")
    async def subscribe_newsletter(self, interaction: discord.Interaction) -> None:
        execute_query(
            """
            INSERT INTO newsletter_subscriptions(discord_guild_id, discord_user_id, channel_id)
            VALUES (?, ?, ?)
            """,
            (str(interaction.guild_id), str(interaction.user.id), str(interaction.channel_id)),
        )
        await interaction.response.send_message(embed=build_success_embed("Subscribed", "You are subscribed to daily newsletter updates."), ephemeral=True)

    @app_commands.command(name="unsubscribe_newsletter", description="Unsubscribe yourself from newsletter updates.")
    async def unsubscribe_newsletter(self, interaction: discord.Interaction) -> None:
        execute_query("UPDATE newsletter_subscriptions SET is_active = 0 WHERE discord_user_id = ?", (str(interaction.user.id),))
        await interaction.response.send_message(embed=build_success_embed("Unsubscribed", "Newsletter subscription disabled."), ephemeral=True)

    @app_commands.command(name="send_newsletter_now", description="Send the daily newsletter now.")
    async def send_newsletter_now(self, interaction: discord.Interaction) -> None:
        guild_id = str(interaction.guild_id)
        await interaction.response.defer(ephemeral=True)
        settings = fetch_one(
            "SELECT newsletter_channel_id FROM guilds WHERE discord_guild_id = ?",
            (guild_id,),
        )
        channel_id = settings.get("newsletter_channel_id") if settings else None
        if not channel_id:
            log_command(str(interaction.user.id), guild_id, "send_newsletter_now", "", "missing_channel")
            await interaction.followup.send(
                embed=build_error_embed("Newsletter channel not set", "Run /set_newsletter_channel in the destination channel first."),
                ephemeral=True,
            )
            return

        ok = await send_newsletter(self.bot, guild_id, channel_id)
        log_command(str(interaction.user.id), guild_id, "send_newsletter_now", channel_id, "success" if ok else "failed")
        if ok:
            await interaction.followup.send(f"Newsletter sent to <#{channel_id}>.", ephemeral=True)
        else:
            await interaction.followup.send("Newsletter failed. Check bot logs for details.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NewsletterCommands(bot))
