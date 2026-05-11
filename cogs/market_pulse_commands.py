import discord
from discord import app_commands
from discord.ext import commands

from database.db import log_command
from services.binance_service import binance_service
from services.market_pulse_service import market_pulse_service
from services.user_service import is_admin
from tasks.market_pulse_task import _process_guild_market_pulse
from utils.embed_builder import build_error_embed, build_success_embed


def admin_only(interaction: discord.Interaction) -> bool:
    return is_admin(str(interaction.user.id))


class MarketPulseCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="set_market_pulse_channel", description="Set the Live Market Pulse channel.")
    @app_commands.check(admin_only)
    async def set_market_pulse_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=build_error_embed("Guild only", "Use this command inside a server."), ephemeral=True)
            return

        settings = market_pulse_service.set_channel(str(interaction.guild.id), str(channel.id))
        log_command(str(interaction.user.id), str(interaction.guild_id), "set_market_pulse_channel", str(channel.id), "success")
        await interaction.response.send_message(
            embed=build_success_embed("Market Pulse Channel Set", f"Live Market Pulse will post in {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="start_market_pulse", description="Enable Live Market Pulse updates.")
    @app_commands.check(admin_only)
    async def start_market_pulse(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=build_error_embed("Guild only", "Use this command inside a server."), ephemeral=True)
            return

        settings = market_pulse_service.start(str(interaction.guild.id))
        log_command(str(interaction.user.id), str(interaction.guild_id), "start_market_pulse", "", "success")
        channel_text = f"<#{settings['channel_id']}>" if settings.get("channel_id") else "No channel configured yet"
        await interaction.response.send_message(
            embed=build_success_embed("Market Pulse Started", f"Automatic updates are enabled.\nChannel: {channel_text}"),
            ephemeral=True,
        )

    @app_commands.command(name="stop_market_pulse", description="Disable Live Market Pulse updates.")
    @app_commands.check(admin_only)
    async def stop_market_pulse(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=build_error_embed("Guild only", "Use this command inside a server."), ephemeral=True)
            return

        market_pulse_service.stop(str(interaction.guild.id))
        log_command(str(interaction.user.id), str(interaction.guild_id), "stop_market_pulse", "", "success")
        await interaction.response.send_message(
            embed=build_success_embed("Market Pulse Stopped", "Automatic market pulse updates are disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="set_market_pulse_coins", description="Set comma-separated symbols for Live Market Pulse.")
    @app_commands.check(admin_only)
    async def set_market_pulse_coins(self, interaction: discord.Interaction, symbols: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=build_error_embed("Guild only", "Use this command inside a server."), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        normalized = market_pulse_service.normalize_symbols(symbols)
        if not normalized:
            await interaction.followup.send(embed=build_error_embed("Invalid Symbols", "Provide symbols like BTCUSDT,ETHUSDT,SOLUSDT."), ephemeral=True)
            return

        invalid_symbols: list[str] = []
        for symbol in normalized:
            if not await binance_service.validate_symbol(symbol):
                invalid_symbols.append(symbol)

        if invalid_symbols:
            log_command(str(interaction.user.id), str(interaction.guild_id), "set_market_pulse_coins", symbols, "invalid")
            await interaction.followup.send(
                embed=build_error_embed("Invalid Symbols", f"Binance did not recognize: {', '.join(invalid_symbols)}"),
                ephemeral=True,
            )
            return

        market_pulse_service.set_symbols(str(interaction.guild.id), ",".join(normalized))
        log_command(str(interaction.user.id), str(interaction.guild_id), "set_market_pulse_coins", ",".join(normalized), "success")
        await interaction.followup.send(
            embed=build_success_embed("Market Pulse Coins Set", ", ".join(normalized)),
            ephemeral=True,
        )

    @app_commands.command(name="set_market_pulse_interval", description="Set price update interval in minutes.")
    @app_commands.check(admin_only)
    async def set_market_pulse_interval(self, interaction: discord.Interaction, minutes: int) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=build_error_embed("Guild only", "Use this command inside a server."), ephemeral=True)
            return
        if minutes < 1:
            await interaction.response.send_message(embed=build_error_embed("Invalid Interval", "Minimum price update interval is 1 minute."), ephemeral=True)
            return

        market_pulse_service.set_update_interval(str(interaction.guild.id), minutes)
        log_command(str(interaction.user.id), str(interaction.guild_id), "set_market_pulse_interval", str(minutes), "success")
        await interaction.response.send_message(
            embed=build_success_embed("Market Pulse Interval Set", f"Price updates will run every {minutes} minute(s)."),
            ephemeral=True,
        )

    @app_commands.command(name="set_market_pulse_chart_interval", description="Set chart update interval in minutes.")
    @app_commands.check(admin_only)
    async def set_market_pulse_chart_interval(self, interaction: discord.Interaction, minutes: int) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=build_error_embed("Guild only", "Use this command inside a server."), ephemeral=True)
            return
        if minutes < 5:
            await interaction.response.send_message(embed=build_error_embed("Invalid Interval", "Minimum chart interval is 5 minutes."), ephemeral=True)
            return

        market_pulse_service.set_chart_interval(str(interaction.guild.id), minutes)
        log_command(str(interaction.user.id), str(interaction.guild_id), "set_market_pulse_chart_interval", str(minutes), "success")
        await interaction.response.send_message(
            embed=build_success_embed("Market Pulse Chart Interval Set", f"Charts will run every {minutes} minute(s)."),
            ephemeral=True,
        )

    @app_commands.command(name="market_pulse_now", description="Send one Live Market Pulse update now.")
    @app_commands.check(admin_only)
    async def market_pulse_now(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=build_error_embed("Guild only", "Use this command inside a server."), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        settings = market_pulse_service.get_or_create_settings(str(interaction.guild.id))
        if not settings.get("channel_id"):
            await interaction.followup.send(
                embed=build_error_embed("No Channel Set", "Run /set_market_pulse_channel first."),
                ephemeral=True,
            )
            return

        await _process_guild_market_pulse(self.bot, settings, force=True)
        log_command(str(interaction.user.id), str(interaction.guild_id), "market_pulse_now", "", "success")
        await interaction.followup.send(embed=build_success_embed("Market Pulse Sent", "A live market pulse update was sent."), ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        embed = build_error_embed("Admin only", "You are not allowed to run this command.")
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MarketPulseCommands(bot))
