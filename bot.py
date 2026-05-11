import asyncio
import logging
from datetime import datetime
import discord
import pytz
from discord.ext import commands

from config import COGS, DISCORD_BOT_TOKEN, TIMEZONE
from database.seed_data import seed_all
from tasks.alert_checker_task import setup_alert_checker_task
from tasks.market_pulse_task import setup_market_pulse_task
from tasks.market_snapshot_task import setup_market_snapshot_task
from tasks.newsletter_task import setup_newsletter_task
from utils.logger import setup_logging


setup_logging()
logger = logging.getLogger("web3_teacher_bot")


class Web3TeacherBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = False
        intents.message_content = True
        super().__init__(command_prefix="=", intents=intents)
        self.newsletter_task = None
        self.market_snapshot_task = None
        self.alert_checker_task = None
        self.market_pulse_task = None
        self._guild_commands_synced = False

    def current_time(self) -> datetime:
        return datetime.now(pytz.timezone(TIMEZONE))

    async def setup_hook(self) -> None:
        seed_all()
        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info("Loaded cog %s", cog)
            except Exception:
                logger.exception("Failed to load cog %s", cog)

        synced = await self.tree.sync()
        logger.info("Synced %s slash commands", len(synced))

        self.newsletter_task = setup_newsletter_task(self)
        self.market_snapshot_task = setup_market_snapshot_task()
        self.alert_checker_task = setup_alert_checker_task(self)
        self.market_pulse_task = setup_market_pulse_task(self)
        self.newsletter_task.start()
        self.market_snapshot_task.start()
        self.alert_checker_task.start()
        self.market_pulse_task.start()

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (%s)", self.user, self.user.id if self.user else "unknown")
        if not self._guild_commands_synced:
            for guild in self.guilds:
                try:
                    self.tree.copy_global_to(guild=guild)
                    synced = await self.tree.sync(guild=guild)
                    logger.info("Synced %s slash commands to guild %s (%s)", len(synced), guild.name, guild.id)
                except Exception:
                    logger.exception("Failed to sync slash commands to guild %s (%s)", guild.name, guild.id)
            self._guild_commands_synced = True
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))

    async def close(self) -> None:
        for task in (self.newsletter_task, self.market_snapshot_task, self.alert_checker_task, self.market_pulse_task):
            if task and task.is_running():
                task.cancel()
        logger.info("Shutting down Web3 Teacher Bot")
        await super().close()


async def main() -> None:
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is missing. Copy .env.example to .env and add your token.")
    bot = Web3TeacherBot()
    async with bot:
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
