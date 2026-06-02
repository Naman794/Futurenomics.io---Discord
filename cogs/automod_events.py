from collections import defaultdict, deque
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from services.server_guard_service import server_guard_service
from utils.formatters import truncate_text


class AutomodEvents(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.message_windows: dict[tuple[int, int], deque[tuple[datetime, str]]] = defaultdict(deque)

    def _is_privileged(self, member: discord.Member) -> bool:
        perms = member.guild_permissions
        return bool(perms.administrator or perms.manage_guild or perms.manage_messages or perms.moderate_members)

    async def _log_channel(self, guild: discord.Guild, settings: dict | None = None):
        settings = settings or server_guard_service.get_active_settings(str(guild.id))
        if not settings or not settings.get("log_channel_id"):
            return None
        channel = guild.get_channel(int(settings["log_channel_id"]))
        if channel is None:
            try:
                channel = await guild.fetch_channel(int(settings["log_channel_id"]))
            except Exception:
                return None
        return channel

    async def _send_log(
        self,
        guild: discord.Guild,
        title: str,
        description: str,
        settings: dict | None = None,
        color: discord.Color | None = None,
    ) -> None:
        channel = await self._log_channel(guild, settings)
        if channel is None:
            return
        embed = discord.Embed(
            title=title,
            description=truncate_text(description, 3900),
            color=color or discord.Color.blue(),
            timestamp=datetime.utcnow(),
        )
        await channel.send(embed=embed)

    def _track_message(self, message: discord.Message, settings: dict) -> tuple[int, int]:
        key = (message.guild.id, message.author.id)
        now = datetime.utcnow()
        window_seconds = int(settings.get("spam_window_seconds") or 8)
        window = self.message_windows[key]
        window.append((now, message.content.strip().lower()))

        while window and (now - window[0][0]).total_seconds() > window_seconds:
            window.popleft()

        recent_count = len(window)
        repeated_count = sum(1 for _, content in window if content and content == message.content.strip().lower())
        return recent_count, repeated_count

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        if not isinstance(message.author, discord.Member):
            return

        settings = server_guard_service.get_active_settings(str(message.guild.id))
        if not settings or self._is_privileged(message.author):
            return

        recent_count, repeated_count = self._track_message(message, settings)
        mention_count = len(message.mentions) + len(message.role_mentions)
        issue = server_guard_service.analyze_message(
            content=message.content,
            settings=settings,
            recent_message_count=recent_count,
            repeated_message_count=repeated_count,
            mention_count=mention_count,
        )
        if issue is None:
            return

        action_taken = "deleted"
        try:
            await message.delete()
        except discord.Forbidden:
            action_taken = "detected_delete_failed"

        violation_count = server_guard_service.record_violation(
            guild_id=str(message.guild.id),
            user_id=str(message.author.id),
            violation_type=issue["type"],
            reason=issue["reason"],
            action_taken=action_taken,
            channel_id=str(message.channel.id),
            message_id=str(message.id),
        )

        timeout_note = ""
        if server_guard_service.should_timeout(settings, violation_count):
            try:
                minutes = int(settings.get("timeout_minutes") or 10)
                await message.author.timeout(
                    datetime.utcnow() + timedelta(minutes=minutes),
                    reason=f"Server Guard: {issue['reason']}",
                )
                timeout_note = f"\nTimed out for {minutes} minute(s)."
                server_guard_service.log_event(
                    guild_id=str(message.guild.id),
                    event_type="auto_timeout",
                    target_user_id=str(message.author.id),
                    channel_id=str(message.channel.id),
                    action_taken="timeout",
                    reason=issue["reason"],
                    metadata={"violation_count": violation_count, "timeout_minutes": minutes},
                )
            except discord.Forbidden:
                timeout_note = "\nTimeout failed: missing role hierarchy or permission."

        await self._send_log(
            message.guild,
            "AutoMod Action",
            f"User: {message.author.mention} (`{message.author.id}`)\n"
            f"Channel: {message.channel.mention}\n"
            f"Violation: `{issue['type']}`\n"
            f"Reason: {issue['reason']}\n"
            f"Action: {action_taken}\n"
            f"Recent violations: {violation_count}"
            f"{timeout_note}\n\n"
            f"Message: {truncate_text(message.content, 900)}",
            settings=settings,
            color=discord.Color.red(),
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        settings = server_guard_service.get_active_settings(str(member.guild.id))
        if not settings:
            return

        auto_role_id = settings.get("auto_role_id")
        if auto_role_id:
            role = member.guild.get_role(int(auto_role_id))
            if role:
                try:
                    await member.add_roles(role, reason="Server Guard auto-role on join")
                    action = f"Auto-role added: {role.name}"
                except discord.Forbidden:
                    action = "Auto-role failed: permission/role hierarchy issue"
            else:
                action = "Auto-role missing"
        else:
            action = "No auto-role configured"

        server_guard_service.log_event(
            guild_id=str(member.guild.id),
            event_type="member_join",
            target_user_id=str(member.id),
            action_taken=action,
            metadata={"username": str(member)},
        )
        await self._send_log(
            member.guild,
            "Member Joined",
            f"User: {member.mention} (`{member.id}`)\nAction: {action}",
            settings=settings,
            color=discord.Color.green(),
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        settings = server_guard_service.get_active_settings(str(member.guild.id))
        if not settings:
            return
        server_guard_service.log_event(
            guild_id=str(member.guild.id),
            event_type="member_leave",
            target_user_id=str(member.id),
            action_taken="logged",
            metadata={"username": str(member)},
        )
        await self._send_log(
            member.guild,
            "Member Left",
            f"User: `{member}` (`{member.id}`)",
            settings=settings,
            color=discord.Color.orange(),
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        settings = server_guard_service.get_active_settings(str(message.guild.id))
        if not settings:
            return
        server_guard_service.log_event(
            guild_id=str(message.guild.id),
            event_type="message_delete",
            target_user_id=str(message.author.id),
            channel_id=str(message.channel.id),
            message_id=str(message.id),
            action_taken="logged",
            metadata={"content": message.content},
        )
        await self._send_log(
            message.guild,
            "Message Deleted",
            f"Author: {message.author.mention} (`{message.author.id}`)\n"
            f"Channel: {message.channel.mention}\n"
            f"Content: {truncate_text(message.content or '[no text content]', 1200)}",
            settings=settings,
            color=discord.Color.orange(),
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild is None or before.author.bot or before.content == after.content:
            return
        settings = server_guard_service.get_active_settings(str(before.guild.id))
        if not settings:
            return
        server_guard_service.log_event(
            guild_id=str(before.guild.id),
            event_type="message_edit",
            target_user_id=str(before.author.id),
            channel_id=str(before.channel.id),
            message_id=str(before.id),
            action_taken="logged",
            metadata={"before": before.content, "after": after.content},
        )
        await self._send_log(
            before.guild,
            "Message Edited",
            f"Author: {before.author.mention} (`{before.author.id}`)\n"
            f"Channel: {before.channel.mention}\n"
            f"Before: {truncate_text(before.content or '[empty]', 900)}\n"
            f"After: {truncate_text(after.content or '[empty]', 900)}",
            settings=settings,
            color=discord.Color.gold(),
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        settings = server_guard_service.get_active_settings(str(after.guild.id))
        if not settings:
            return

        changes = []
        if before.nick != after.nick:
            changes.append(f"Nickname: `{before.nick}` → `{after.nick}`")

        before_roles = {role.id: role for role in before.roles}
        after_roles = {role.id: role for role in after.roles}
        added = [role.name for role_id, role in after_roles.items() if role_id not in before_roles]
        removed = [role.name for role_id, role in before_roles.items() if role_id not in after_roles]
        if added:
            changes.append("Roles added: " + ", ".join(added))
        if removed:
            changes.append("Roles removed: " + ", ".join(removed))

        if not changes:
            return

        server_guard_service.log_event(
            guild_id=str(after.guild.id),
            event_type="member_update",
            target_user_id=str(after.id),
            action_taken="logged",
            metadata={"changes": changes},
        )
        await self._send_log(
            after.guild,
            "Member Updated",
            f"User: {after.mention} (`{after.id}`)\n" + "\n".join(changes),
            settings=settings,
            color=discord.Color.blue(),
        )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel) -> None:
        await self._log_structure_event(channel.guild, "Channel Created", f"Channel: {channel.mention} (`{channel.id}`)", "channel_create")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel) -> None:
        await self._log_structure_event(channel.guild, "Channel Deleted", f"Channel: `{channel.name}` (`{channel.id}`)", "channel_delete")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after) -> None:
        if before.name == after.name:
            return
        await self._log_structure_event(after.guild, "Channel Updated", f"Channel: {after.mention}\nName: `{before.name}` → `{after.name}`", "channel_update")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        await self._log_structure_event(role.guild, "Role Created", f"Role: `{role.name}` (`{role.id}`)", "role_create")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        await self._log_structure_event(role.guild, "Role Deleted", f"Role: `{role.name}` (`{role.id}`)", "role_delete")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        if before.name == after.name and before.permissions == after.permissions:
            return
        await self._log_structure_event(
            after.guild,
            "Role Updated",
            f"Role: `{after.name}` (`{after.id}`)\nPrevious name: `{before.name}`",
            "role_update",
        )

    async def _log_structure_event(self, guild: discord.Guild, title: str, description: str, event_type: str) -> None:
        settings = server_guard_service.get_active_settings(str(guild.id))
        if not settings:
            return
        server_guard_service.log_event(
            guild_id=str(guild.id),
            event_type=event_type,
            action_taken="logged",
            metadata={"description": description},
        )
        await self._send_log(guild, title, description, settings=settings)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutomodEvents(bot))
