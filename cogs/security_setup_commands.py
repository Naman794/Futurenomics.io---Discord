import discord
from discord import app_commands
from discord.ext import commands

from database.db import log_command
from services.server_guard_service import server_guard_service
from services.user_service import is_admin
from utils.embed_builder import build_error_embed, build_success_embed


LOG_CHANNEL_NAME = "server-logs"
AUTO_ROLE_NAME = "Futurenomics Member"
QUARANTINE_ROLE_NAME = "Quarantined"


def admin_only(interaction: discord.Interaction) -> bool:
    return is_admin(str(interaction.user.id)) or bool(interaction.user.guild_permissions.administrator)


class SecuritySetupCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup", description="Set up automated server guard, logs, roles, and anti-spam protection.")
    @app_commands.check(admin_only)
    async def setup(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=build_error_embed("Guild only", "Run this command inside your Discord server."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        me = guild.me
        if me is None:
            await interaction.followup.send("Bot member not found in this guild.", ephemeral=True)
            return

        missing = self._missing_permissions(me.guild_permissions)
        if missing:
            await interaction.followup.send(
                embed=build_error_embed(
                    "Missing Bot Permissions",
                    "Give the bot these permissions first:\n" + "\n".join(f"- {item}" for item in missing),
                ),
                ephemeral=True,
            )
            return

        log_channel = await self._get_or_create_log_channel(guild)
        auto_role = await self._get_or_create_role(guild, AUTO_ROLE_NAME, discord.Color.green())
        quarantine_role = await self._get_or_create_role(guild, QUARANTINE_ROLE_NAME, discord.Color.dark_red())
        await self._apply_quarantine_overwrites(guild, quarantine_role)

        settings = server_guard_service.upsert_settings(
            guild_id=str(guild.id),
            guild_name=guild.name,
            log_channel_id=str(log_channel.id),
            auto_role_id=str(auto_role.id),
            quarantine_role_id=str(quarantine_role.id),
        )
        server_guard_service.log_event(
            guild_id=str(guild.id),
            event_type="setup",
            actor_user_id=str(interaction.user.id),
            action_taken="enabled",
            reason="Automated server guard setup completed.",
            metadata={
                "log_channel_id": str(log_channel.id),
                "auto_role_id": str(auto_role.id),
                "quarantine_role_id": str(quarantine_role.id),
            },
        )
        log_command(str(interaction.user.id), str(guild.id), "setup", "", "success")

        await log_channel.send(
            embed=build_success_embed(
                "Server Guard Enabled",
                "Automated protection is now active.\n"
                "- Join/leave logs enabled\n"
                "- Message edit/delete logs enabled\n"
                "- Role/channel/member change logs enabled\n"
                "- Auto-role enabled\n"
                "- Anti-spam, anti-link, anti-invite, anti-caps, anti-mention filters enabled\n"
                "- Repeat violators will be timed out automatically",
            )
        )

        await interaction.followup.send(
            embed=build_success_embed(
                "Setup Complete",
                f"Server Guard is active.\nLogs: {log_channel.mention}\nAuto-role: {auto_role.mention}\nQuarantine role: {quarantine_role.mention}",
            ),
            ephemeral=True,
        )

    def _missing_permissions(self, permissions: discord.Permissions) -> list[str]:
        required = {
            "manage_channels": "Manage Channels",
            "manage_roles": "Manage Roles",
            "manage_messages": "Manage Messages",
            "moderate_members": "Moderate Members",
            "view_audit_log": "View Audit Log",
            "send_messages": "Send Messages",
            "embed_links": "Embed Links",
            "read_message_history": "Read Message History",
        }
        return [label for key, label in required.items() if not getattr(permissions, key)]

    async def _get_or_create_log_channel(self, guild: discord.Guild) -> discord.TextChannel:
        existing = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if existing:
            return existing

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, read_message_history=True),
        }
        for role in guild.roles:
            if role.permissions.administrator or role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

        return await guild.create_text_channel(
            LOG_CHANNEL_NAME,
            overwrites=overwrites,
            reason="Futurenomics automated server guard setup",
        )

    async def _get_or_create_role(self, guild: discord.Guild, name: str, color: discord.Color) -> discord.Role:
        existing = discord.utils.get(guild.roles, name=name)
        if existing:
            return existing
        return await guild.create_role(
            name=name,
            color=color,
            reason="Futurenomics automated server guard setup",
        )

    async def _apply_quarantine_overwrites(self, guild: discord.Guild, role: discord.Role) -> None:
        overwrite = discord.PermissionOverwrite(
            send_messages=False,
            send_messages_in_threads=False,
            create_public_threads=False,
            create_private_threads=False,
            add_reactions=False,
        )
        for channel in guild.text_channels:
            try:
                await channel.set_permissions(role, overwrite=overwrite, reason="Apply quarantine role restrictions")
            except discord.Forbidden:
                continue

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        embed = build_error_embed("Admin only", "You are not allowed to run /setup.")
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SecuritySetupCommands(bot))
