from discord.ext import tasks

from config import DISCLAIMER
from services.alert_service import check_active_alerts
from utils.formatters import format_price


def setup_alert_checker_task(bot):
    @tasks.loop(minutes=2)
    async def alert_checker():
        for alert in await check_active_alerts():
            user = await bot.fetch_user(int(alert["discord_user_id"]))
            await user.send(
                f"Price alert triggered: {alert['symbol']} is {format_price(alert['current_price'])}, "
                f"{alert['condition_type']} {format_price(alert['target_price'])}.\n{DISCLAIMER}"
            )

    return alert_checker
