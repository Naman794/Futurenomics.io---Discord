from discord.ext import tasks

from config import NEWSLETTER_HOUR, NEWSLETTER_MINUTE
from database.db import fetch_all
from services.newsletter_service import send_newsletter


def setup_newsletter_task(bot):
    @tasks.loop(minutes=1)
    async def daily_newsletter():
        now = bot.current_time()
        if now.hour != NEWSLETTER_HOUR or now.minute != NEWSLETTER_MINUTE:
            return
        guilds = fetch_all("SELECT discord_guild_id, newsletter_channel_id FROM guilds WHERE newsletter_channel_id IS NOT NULL")
        for guild in guilds:
            await send_newsletter(bot, guild["discord_guild_id"], guild["newsletter_channel_id"])

    return daily_newsletter
