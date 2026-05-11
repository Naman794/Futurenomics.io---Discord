import discord
from discord import app_commands
from discord.ext import commands

from database.db import execute_query, fetch_all, fetch_one
from services.newsletter_service import send_newsletter
from services.user_service import is_admin
from utils.embed_builder import build_error_embed, build_success_embed


def admin_only(interaction: discord.Interaction) -> bool:
    return is_admin(str(interaction.user.id))


class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="admin_stats", description="Show bot stats.")
    @app_commands.check(admin_only)
    async def admin_stats(self, interaction: discord.Interaction) -> None:
        users = fetch_one("SELECT COUNT(*) AS count FROM users")["count"]
        commands = fetch_one("SELECT COUNT(*) AS count FROM command_logs")["count"]
        await interaction.response.send_message(embed=build_success_embed("Admin Stats", f"Users: {users}\nCommands: {commands}"), ephemeral=True)

    @app_commands.command(name="admin_force_newsletter", description="Force newsletter to current channel.")
    @app_commands.check(admin_only)
    async def admin_force_newsletter(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        ok = await send_newsletter(self.bot, str(interaction.guild_id), str(interaction.channel_id))
        await interaction.followup.send("Sent." if ok else "Failed.", ephemeral=True)

    @app_commands.command(name="admin_add_lesson", description="Add or replace a lesson.")
    @app_commands.check(admin_only)
    async def admin_add_lesson(self, interaction: discord.Interaction, topic_slug: str, title: str, content: str) -> None:
        execute_query(
            """
            INSERT INTO lessons(topic_slug, title, category, level, content)
            VALUES (?, ?, 'web3', 'beginner', ?)
            ON CONFLICT(topic_slug) DO UPDATE SET title = excluded.title, content = excluded.content, updated_at = CURRENT_TIMESTAMP
            """,
            (topic_slug.lower(), title, content),
        )
        await interaction.response.send_message(embed=build_success_embed("Lesson saved", title), ephemeral=True)

    @app_commands.command(name="admin_logs", description="Show recent command logs.")
    @app_commands.check(admin_only)
    async def admin_logs(self, interaction: discord.Interaction) -> None:
        rows = fetch_all("SELECT command_name, response_status, created_at FROM command_logs ORDER BY id DESC LIMIT 10")
        text = "\n".join(f"{r['created_at']} - {r['command_name']} - {r['response_status']}" for r in rows) or "No logs."
        await interaction.response.send_message(embed=build_success_embed("Recent Logs", text), ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        await interaction.response.send_message(embed=build_error_embed("Admin only", "You are not allowed to run this command."), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCommands(bot))
